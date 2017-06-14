#include "../processor.h"
#include "../codemanager.h"
#include "../cstruct.h"
#include "../blockalloc.h"
#include "../Python/frames.h"
#include "ivm-insns.h"


/* We distinguish between different types of interpreters:
 *  - the most compatible one is switch()-based
 *  - a GCC extension allows absolute threaded jumps
 *  - a more recent GCC extension allows relative threaded jumps
 *    (not sure that it is better than the previous one, though;
 *     will need some tests)
 */
#ifdef __GNUC__
# define VM_THREADED_INTERPRETER   1
# define VM_RELATIVE_JUMPS  0   /* XXX check if this is really better */
//# define VM_RELATIVE_JUMPS  (__GNUC__>3||(__GNUC__==3&&__GNUC_MINOR__>=2))
#else
# define VM_THREADED_INTERPRETER   0
#endif


/***************************************************************/
 /***  Stack of the virtual machine                           ***/

/* Note that the stack grows downwards. */
/* See ivm-insns.h for customizable parameters. */

/* XXX loafy stack overflow checking ahead */

#define FINFO_STOP  ((struct stack_frame_info_s*) 1)

typedef struct vmstackframe_s vmstackframe_t;
struct vmstackframe_s {
	struct stack_frame_info_s* finfo;  /* describes the *called* (i.e. next
					      frame's) function (this is for
					      compatibility with the hacks needed
					      for real machine code */
	char* limit;
	char* sp;      /* stack pointer: limit<=sp<=origin */
	char* origin;
	vmstackframe_t* prevframe;    /* the previous frame */
	vmstackframe_t* nextframe;    /* the next more recent frame */
};

BLOCKALLOC_STATIC(vmstackframe, vmstackframe_t, 256)

typedef struct {
	PyCStruct_HEAD
	vmstackframe_t* topframe;     /* most recent stack frame */
} PyVMStack;

PSY_INLINE PyVMStack* vm_get_stack(PyObject* tdict)
{
	PyVMStack* st;
	RECLIMIT_SAFE_ENTER();
	st = (PyVMStack*) PyDict_GetItem(tdict, Py_None);
	if (st == NULL) {
		st = PyCStruct_NEW(PyVMStack, NULL);
		st->topframe = NULL;
		if (PyDict_SetItem(tdict, Py_None, (PyObject*) st))
			OUT_OF_MEMORY();
	}
	RECLIMIT_SAFE_LEAVE();
	return st;
}


/***************************************************************/
 /***  Virtual machine interpreter                            ***/

#define bytecode_nextopcode()   (*nextip++)
#define bytecode_nx_code_t()    (*nextip++)
#define bytecode_nx_word_t()    (tmp = *(word_t*) nextip,	\
				 nextip += sizeof(word_t),	\
				 tmp)
#define bytecode_nx_char()      ((char)(*nextip++))
#define bytecode_next(T)        (bytecode_nx_##T())

#define stack_nth(N)            sp[N]
#define stack_shift(N)          (sp += (N),                     \
                                 extra_assert((char*)sp >= frame->limit))
#define stack_shift_pos(N)      (sp += (N))
#define stack_savesp()          (frame->sp = (char*) sp)

#define macro_args              /* nothing */
#define macro_noarg             ()  /* macro call with no argument */

PSY_INLINE long abs_o(long a) { return a < 0 ? -a : a; }
#define ovf_checkabs_o(a)       (a == LONG_MIN)
#define ovf_checkneg_o(a)       (a == LONG_MIN)
#define ovf_checkadd_o(a, b)    (((a+b)^a) < 0 && (a^b) >= 0)
#define ovf_checksub_o(a, b)    (((a-b)^a) < 0 && ((a-b)^b) >= 0)
#define ovf_checkmul_o(a, b)    psyco_int_mul_ovf(a, b)
#define ovf_check(INSN, ARGS)   ovf_check##INSN ARGS

#define impl_stackgrow(sz)      if ((char*)sp - frame->limit <		\
				    (sz) + VM_STACK_SIZE_MARGIN)	\
				    sp = vm_stackgrow(frame, sp)
#define impl_jcond(test, newip) if (test) nextip = (code_t*) newip
#define impl_jump(newip)        nextip = (code_t*) newip
typedef code_t* (*cbuild1_fn) (char*);
typedef code_t* (*cbuild2_fn) (char*, word_t extra);
#define impl_cbuild1(fn)        stack_savesp();					\
                                nextip = ((cbuild1_fn) fn) (			\
                                    (char*)((((long)nextip) + PSYCO_DEBUG +	\
					    ALIGN_CODE_MASK)&~ALIGN_CODE_MASK))
#define impl_cbuild2(fn, extra) stack_savesp();					\
                                nextip = ((cbuild2_fn) fn) (			\
                                    (char*)((((long)nextip) + PSYCO_DEBUG +	\
					    ALIGN_CODE_MASK)&~ALIGN_CODE_MASK),	\
				    extra)
#define impl_incref(o)          Py_INCREF((PyObject*) o)
#define impl_decref(o)          stack_savesp(); Py_DECREF((PyObject*) o)
#define impl_decrefnz(o)        ((PyObject*) o)->ob_refcnt--
/* implemented in pycompiler.c */
EXTERNFN void cimpl_finalize_frame_locals(PyObject*, PyObject*, PyObject*);
#define impl_exitframe(tb, val, exc)  stack_savesp();				\
                                      if (exc) cimpl_finalize_frame_locals(	\
                                                   (PyObject*) exc,		\
                                                   (PyObject*) val,		\
                                                   (PyObject*) tb)
#define impl_pyenter(finfo)     frame = vm_pyenter(vmst, frame, finfo, sp)
#define impl_pyleave            frame = vm_pyleave(vmst, frame, sp);	        \
                                sp = (word_t*) frame->sp;
/* XXX hack! We abuse the fact that frame->sp is not completely in sync with
   the local sp (this is the case for optimization purposes). When impl_vmcall()
   is called, frame->sp still has the value it had at the last impl_pyenter()
   (see iencoding.c:psyco_call_psyco()). */
#define impl_vmcall(target)     (tmp=(word_t) nextip,		\
				 nextip=(code_t*) target,	\
                                 frame->origin = frame->sp,     \
				 tmp)
#define impl_ret(retaddr)       if (retaddr == 0) {				\
                                    return retval;				\
                                } else {					\
                                    nextip = (code_t*) retaddr;			\
                                }
/* XXX divide the stack in separately-growable blocks across INSN_vmcall() */
typedef word_t (*ccalled_fn_t_0) (void);
typedef word_t (*ccalled_fn_t_1) (word_t);
typedef word_t (*ccalled_fn_t_2) (word_t,word_t);
typedef word_t (*ccalled_fn_t_3) (word_t,word_t,word_t);
typedef word_t (*ccalled_fn_t_4) (word_t,word_t,word_t,word_t);
typedef word_t (*ccalled_fn_t_5) (word_t,word_t,word_t,word_t,word_t);
typedef word_t (*ccalled_fn_t_6) (word_t,word_t,word_t,word_t,word_t,word_t);
typedef word_t (*ccalled_fn_t_7) (word_t,word_t,word_t,word_t,word_t,word_t,word_t);
#define impl_ccall(nbargs, fn, args)  (stack_savesp(),				\
                                       (((ccalled_fn_t_##nbargs)(fn)) args))
#define impl_checkdict(dict, key, result, index)    (				\
	(unsigned)((PyDictObject*)dict)->ma_mask < (unsigned)index ||		\
	((PyDictObject*)dict)->ma_table[index].me_key != (PyObject*)key ||	\
	((PyDictObject*)dict)->ma_table[index].me_value != (PyObject*)result)
#define impl_dynamicfreq        (((word_t*) nextip)[-1] ++)
#if PSYCO_DEBUG
# define impl_debug_check_flag(x)   extra_assert(x == 0 || x == 1)
# define impl_debug_forget_flag(x)  x = 0xABABABAB
#else
# define impl_debug_check_flag(x)   /* nothing */
# define impl_debug_forget_flag(x)  /* nothing */
#endif

PSY_INLINE vmstackframe_t* vm_pyenter(PyVMStack* vmst, vmstackframe_t* frame,
				  word_t finfo, word_t* currentsp)
{
	vmstackframe_t* top = psyco_llalloc_vmstackframe();
	top->finfo  = FINFO_STOP;
	top->limit  = frame->limit;
	top->sp     = frame->sp = (char*) currentsp;
	top->origin = frame->origin;
	top->prevframe = frame;
	top->nextframe = NULL;
	frame->finfo = (struct stack_frame_info_s*) finfo;
	frame->nextframe = top;
	vmst->topframe = top;
	return top;
}
PSY_INLINE vmstackframe_t* vm_pyleave(PyVMStack* vmst, vmstackframe_t* top,
				  word_t* currentsp)
{
	vmstackframe_t* prevtop = top->prevframe;
	prevtop->finfo = FINFO_STOP;
	prevtop->nextframe = NULL;
	
	if (prevtop->limit != top->limit) {
		/* only when leaving an non-inlined subfunction.
		   Then prevtop->sp already contains the equivalent
		   pointer to restore. This only works if the pyleave
		   instruction is immediately after vmcall, because
		   it assumes that the stack has the same depth as when
		   pyenter was called (which is false when pyleave is
		   used for an inlined subfunction). */
		PyMem_Free(top->limit);
	}
	else {
		prevtop->sp = (char*) currentsp;
	}
	vmst->topframe = prevtop;
	psyco_llfree_vmstackframe(top);
	return prevtop;
}
static word_t* vm_stackgrow(vmstackframe_t* frame, word_t* currentsp)
{
	/* enlarge the stack of the topmost frame 'frame'
	   and all the previous frames which share exactly the same stack */
	vmstackframe_t* f;
	char* currentlimit  = frame->limit;
	char* currentorigin = frame->origin;
	char* newsp;
	size_t cursize = currentorigin - (char*)currentsp;
	size_t newsize = cursize + VM_EXTRA_STACK_SIZE+2*VM_STACK_SIZE_MARGIN-1;
	newsize &= -VM_STACK_SIZE_MARGIN;
	frame->limit = PyMem_Malloc(newsize);
	if (frame->limit == NULL)
		OUT_OF_MEMORY();
	frame->origin = frame->limit + newsize;
	newsp = frame->origin - cursize;
	memcpy(newsp, currentsp, cursize);

	for (f = frame->prevframe;
	     f != NULL && f->limit == currentlimit;
	     f = f->prevframe) {
		if (f->origin == currentorigin) {
			/* exactly the same stack, fix it too */
			f->limit = frame->limit;
			f->origin = frame->origin;
			f->sp = newsp;
		}
		else {
			/* previous frame has a larger stack starting
			   from the same position, which means it is from
			   a parent function -- the child function's stack
			   is smaller because it does not contain everything
			   past the input arguments. In this case there is
			   no old stack to free because the old stack is
			   still in use. */
			return (word_t*) newsp;
		}
	}
	/* free old stack */
	PyMem_Free(currentlimit);
	return (word_t*) newsp;
}

/* on register-limited architectures it may help a little bit
   to force these local variables in registers, as the compiler
   may think it would be better not to. */

#if defined(__GNUC__) && !PSYCO_DEBUG
# ifdef __i386__
#  define F_SPREG      asm("esi")
#  define F_NEXTIPREG  asm("edi")
# endif
#endif


#ifndef F_ACCUMREG
# define F_ACCUMREG   /* nothing */
#endif
#ifndef F_SPREG
# define F_SPREG      /* nothing */
#endif
#ifndef F_NEXTIPREG
# define F_NEXTIPREG  /* nothing */
#endif


#define retval  flag   /* same ivm register */

static word_t vm_interpreter_main_loop(PyVMStack* vmst)
{
	/* virtual machine "registers" */
	register word_t accum F_ACCUMREG; /* 1st stack item, for optimization */
	register word_t* sp    F_SPREG;       /* stack pointer */
	register code_t* nextip F_NEXTIPREG;   /* next instruction pointer */
	word_t flag;                            /* flags OR retval register */
	word_t tmp;
	vmstackframe_t* frame = vmst->topframe;

	/* initialization */
	nextip    = (code_t*) frame->limit; /* hack from psyco_processor_run() */
	sp        = (word_t*) frame->sp;
	accum     = 0xCDCDCDCD;  /* unused */
	flag      = 0xCDCDCDCD;  /* unused */

	/* Let's loop! */
#	if VM_THREADED_INTERPRETER
	{
#		if VM_RELATIVE_JUMPS
#			include "prolog/insns-threaded-rel.i"
#		else
#			include "prolog/insns-threaded.i"
#		endif
	}
#	else
	while (1) {
		switch (bytecode_nextopcode()) {
#			include "prolog/insns-switch.i"
		default:
			psyco_fatal_msg("invalid vm opcode");
		}
	}
#	endif
}

#undef retval


/***************************************************************/
 /***  Virtual machine entry point                            ***/

#define VM_ENOUGH_STACK                                                 \
	    (top->origin - top->limit >= (int)(4*sizeof(long)*argc +    \
	     VM_INITIAL_MINIMAL_STACK_SIZE + VM_STACK_SIZE_MARGIN))

DEFINEFN
PyObject* psyco_processor_run(CodeBufferObject* codebuf,
                              long initial_stack[],
                              struct stack_frame_info_s*** finfo,
                              PyObject* tdict)
{
	PyObject* result;
	PyVMStack* vmst = vm_get_stack(tdict);
	vmstackframe_t* prevtop = vmst->topframe;
	vmstackframe_t* top = psyco_llalloc_vmstackframe();
	*finfo = &top->finfo;
	top->finfo = FINFO_STOP;
	top->prevframe = prevtop;
	top->nextframe = NULL;
	if (prevtop) {
		top->limit  = prevtop->limit;
		top->origin = prevtop->sp;  /* start using the stack from
					       the prevtop's current sp */
	}
	else {
		top->limit  = NULL;
		top->origin = NULL;
	}

	/* to store the incoming arguments on the stack,
	   the "cleanest" solution seems to be to build a temporary
	   pseudo-code. The not-so-clean hack is to abuse the stack
	   to write this code. */
	{
		int argc = RUN_ARGC(codebuf);
		word_t* arg;
		code_t* code;

		if (!VM_ENOUGH_STACK) {
			top->limit = PyMem_Malloc(VM_STACK_BLOCK);
			if (!top->limit)
				OUT_OF_MEMORY();
			top->origin = top->limit + VM_STACK_BLOCK;
			extra_assert(VM_ENOUGH_STACK);
		}
		top->sp = top->origin;

		code = (code_t*) top->limit;
		INIT_CODE_EMISSION(code);
		while (argc) {   /* incoming arguments */
			long argvalue = initial_stack[--argc];
			INSN_immed(argvalue);
		}
		INSN_immed(0);   /* return address. Special value 0 means
				    "leave the interpreter main loop" */
		INSN_jumpfar(&arg);
		*arg = (word_t) codebuf->codestart;
	}

	vmst->topframe = top;
	result = (PyObject*) vm_interpreter_main_loop(vmst);
	vmst->topframe = prevtop;

	/* restore the stack */
	if (prevtop == NULL || top->limit != prevtop->limit) {
		PyMem_Free(top->limit);
	}
	psyco_llfree_vmstackframe(top);
	return result;
}


/***************************************************************/
 /***  Misc                                                   ***/

static struct stack_frame_info_s* finfo_stop = FINFO_STOP;

DEFINEFN struct stack_frame_info_s**
psyco_next_stack_frame(struct stack_frame_info_s** finfo)
{
	vmstackframe_t* frame = (vmstackframe_t*) finfo;
	extra_assert(finfo == &frame->finfo);
	if (frame->nextframe == NULL)
		return &finfo_stop;
	else
		return &frame->nextframe->finfo;
}

/* check for signed integer multiplication overflow */
/* code shamelessly ripped off Python's intobject.c */
static char python_style_mul_ovf(long a, long b)
{
	long longprod;			/* a*b in native long arithmetic */
	double doubled_longprod;	/* (double)longprod */
	double doubleprod;		/* (double)a * (double)b */

	longprod = a * b;
	doubleprod = (double)a * (double)b;
	doubled_longprod = (double)longprod;

	/* Fast path for normal case:  small multiplicands, and no info
	   is lost in either method. */
	if (doubled_longprod == doubleprod)
		return false;  /* no overflow */

	/* Somebody somewhere lost info.  Close enough, or way off?  Note
	   that a != 0 and b != 0 (else doubled_longprod == doubleprod == 0).
	   The difference either is or isn't significant compared to the
	   true value (of which doubleprod is a good approximation).
	*/
	{
		const double diff = doubled_longprod - doubleprod;
		const double absdiff = diff >= 0.0 ? diff : -diff;
		const double absprod = doubleprod >= 0.0 ? doubleprod :
							  -doubleprod;
		/* absdiff/absprod <= 1/32 iff
		   32 * absdiff <= absprod -- 5 good bits is "close enough" */
		return !(32.0 * absdiff <= absprod);
	}
}

DEFINEVAR char (*psyco_int_mul_ovf) (long a, long b) = &python_style_mul_ovf;


/* don't look */
static long hacky_call_var(void* c_func, int argcount, long arguments[])
{
	switch (argcount) {
	case 0: return ((ccalled_fn_t_0) c_func) ();
	case 1: return ((ccalled_fn_t_1) c_func) (arguments[0]);
	case 2: return ((ccalled_fn_t_2) c_func) (arguments[0],
						  arguments[1]);
	case 3: return ((ccalled_fn_t_3) c_func) (arguments[0],
						  arguments[1],
						  arguments[2]);
	case 4: return ((ccalled_fn_t_4) c_func) (arguments[0],
						  arguments[1],
						  arguments[2],
						  arguments[3]);
	case 5: return ((ccalled_fn_t_5) c_func) (arguments[0],
						  arguments[1],
						  arguments[2],
						  arguments[3],
						  arguments[4]);
	case 6: return ((ccalled_fn_t_6) c_func) (arguments[0],
						  arguments[1],
						  arguments[2],
						  arguments[3],
						  arguments[4],
						  arguments[5]);
	case 7: return ((ccalled_fn_t_7) c_func) (arguments[0],
						  arguments[1],
						  arguments[2],
						  arguments[3],
						  arguments[4],
						  arguments[5],
						  arguments[6]);
	default: psyco_fatal_msg("too many arguments to C function call");
	}
	return 0;
}

DEFINEVAR long (*psyco_call_var) (void* c_func, int argcount, long arguments[]) =
		&hacky_call_var;
