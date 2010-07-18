 /***************************************************************/
/***            Processor-specific code generation             ***/
 /***************************************************************/

#ifndef _CODEGEN_H
#define _CODEGEN_H


#include "vcompiler.h"
#include <iencoding.h>

#if SIZEOF_LONG == 4
# define SIZE_OF_LONG_BITS   2
#else
# error "-----------------------------------------------------"
# error "Sorry, non-32-bit platforms are not supported at all."
# error "You may try with a Python compiled in 32-bit         "
# error "compatibility mode.  Note that Psyco will probably   "
# error "never support non-32-bit platforms, as it is no      "
# error "longer actively developed.  Instead, the PyPy group  "
# error "plans to replace it with a more flexible and easily  "
# error "retargettable Psyco-for-PyPy during the year 2006.   "
# error "See http://codespeak.net/pypy/                       "
# error "-----------------------------------------------------"
#endif

#if SIZEOF_LONG != SIZEOF_VOID_P
# error "Sorry, your platform is not supported at all."
# error "Psyco currently requires sizeof(long)==sizeof(void*)."
#endif

#define INITIAL_STACK_DEPTH  4 /* anything >0 and a multiple of 4 */


/***************************************************************/
 /*** Condition Codes (a.k.a. the processor 'flags' register) ***/

/* return a new vinfo_t* meaning `in the processor flags, true if <cc>',
   as an integer 0 or 1.  The source of the vinfo_t* is compile-time
   if cc is CC_ALWAYS_TRUE/FALSE, and virtual-time otherwise. */
EXTERNFN vinfo_t* psyco_vinfo_condition(PsycoObject* po, condition_code_t cc);
EXTERNFN VirtualTimeSource psyco_source_condition(condition_code_t cc);

/* if 'source' comes from psyco_vinfo_condition(), return its <cc>;
   otherwise return CC_ALWAYS_FALSE. */
#if HAVE_CCREG
EXTERNFN condition_code_t psyco_vsource_cc(Source source);
EXTERNFN void psyco_resolved_cc(PsycoObject* po, condition_code_t cc_known_true);
#else
# define psyco_vsource_cc(src)  CC_ALWAYS_FALSE
#endif


/***************************************************************/
 /*** Read/write memory                                       ***/

/* access the data word at address 'nv_ptr + offset + (rt_vindex<<size2)'.
   'nv_ptr' must be a non-virtual source.
   'rt_vindex' must be a run-time source or NULL.
   '1<<size2' also specifies the size of the data word to access.
   '1<<size2' must be 1, 2, 4 or 8 (in the latter case, only the first 4 bytes
     are accessed anyway).
   'nonsigned' selects between zero- and sign-extension
     if '1<<size2' is 1 or 2. */
EXTERNFN vinfo_t* psyco_memory_read(PsycoObject* po, vinfo_t* nv_ptr,
                                    long offset, vinfo_t* rt_vindex,
                                    int size2, bool nonsigned);
EXTERNFN bool psyco_memory_write(PsycoObject* po, vinfo_t* nv_ptr,
                                 long offset, vinfo_t* rt_vindex,
                                 int size2, vinfo_t* value);


#if 0
/* XXX to do: references from the code buffers. This is tricky because
   we can have quite indirect references, or references to a subobject of
   a Python object, or to a field only of a Python object, etc... */
PSY_INLINE long reference_from_code(PsycoObject* po, CompileTimeSource source)
{
	--- DISABLED ---
	source_known_t* sk = CompileTime_Get(source);
	if ((sk->refcount1_flags & SkFlagPyObj) != 0) {
		/* XXX we get a reference from the code.
		   Implement freeing such references
		   together with code buffers. */
		sk_incref(sk);
	}
	return sk->value;
}
#endif


/*****************************************************************/
 /***   Calling C functions                                     ***/

/* A generic way of emitting the call to a C function.
   For maximal performance you can also directly use the macros
   CALL_C_FUNCTION()&co. in encoding.h.

   'arguments' is a string describing the following arguments
   of psyco_generic_call(). Each argument to the C function to call
   comes from a 'vinfo_t*' structure, excepted when it is known to be
   compile-time, in which case a 'long' or 'PyObject*' can be passed
   instead. In 'arguments' the characters are interpreted as follows:

      l      an immediate 'long' or 'PyObject*' value
      v      a 'vinfo_t*' value
      r      a run-time 'vinfo_t*' value passed as a reference
      a      a 'vinfo_array_t*' used by the C function as output buffer
      A      same as 'a', but the C function creates new references

   'r' means that the C function wants to get a reference to a
   single-word value (typically it is an output argument). The
   run-time value is pushed in the stack if it is just in a
   register. Incompatible with CfPure.

   'a' means that the C function gets a pointer to a buffer capable of
   containing as many words as specified by the array count.
   psyco_generic_call() fills the array with run-time vinfo_ts
   representing the output values.
*/
EXTERNFN vinfo_t* psyco_generic_call(PsycoObject* po, void* c_function,
                                     int flags, const char* arguments, ...);

/* if the C function has no side effect it can be called at compile-time
   if all its arguments are compile-time. Use CfPure in this case. */
#define CfPure           0x10

/* if the C function returns a long or a PyObject* but not a new reference */
#define CfReturnNormal   0x00   /* default */

/* if the C function returns a new reference */
#define CfReturnRef      0x01

/* if the C function does not return anything
   or if you are not interested in getting the result in a vinfo_t.
   psyco_generic_call() returns anything non-NULL (unless there is an error)
   in this case. */
#define CfNoReturnValue  0x03

#define CfReturnMask     0x0F
/* See also the Python-specific flags CfPyErrXxx defined in pycheader.h. */


/* To emit the call to other code blocks emitted by Psyco. 'argsources' gives
   the run-time sources for the arguments, as specified by
   psyco_build_frame(). */
EXTERNFN vinfo_t* psyco_call_psyco(PsycoObject* po, CodeBufferObject* codebuf,
				   Source argsources[], int argcount,
				   struct stack_frame_info_s* finfo);

PSY_INLINE int get_arguments_count(vinfo_array_t* vlocals) {
	int retpos = getstack(vlocals->items[INDEX_LOC_CONTINUATION]->source);
	extra_assert(retpos != RunTime_StackNone);
	return (retpos-(INITIAL_STACK_DEPTH+sizeof(long))) / sizeof(long);
}

/* Emit the code to mark the presence of an inlined frame */
EXTERNFN void psyco_inline_enter(PsycoObject* po);
EXTERNFN void psyco_inline_exit (PsycoObject* po);


/*****************************************************************/
 /***   Emit common instructions                                ***/

/* Returns a condition code for: "'vi' is not null". Warning, when a
   function returns a condition code it must be used immediately, before
   there is any chance for new code to be emitted. If you are unsure, use
   psyco_vinfo_condition() to turn the condition code into a 0 or 1 integer. */
EXTERNFN condition_code_t integer_non_null(PsycoObject* po, vinfo_t* vi);

/* Same as above, but consumes the reference on 'vi'. Also checks if
   'vi==NULL' and returns CC_ERROR in this case. */
EXTERNFN condition_code_t integer_NON_NULL(PsycoObject* po, vinfo_t* vi);

/* Instructions with an 'ovf' parameter will check for overflow
   if 'ovf' is true. They return NULL if an overflow is detected. */
EXTERNFN
vinfo_t* integer_add  (PsycoObject* po, vinfo_t* v1, vinfo_t* v2, bool ovf);
EXTERNFN   /* 'unsafe': optimize by silently assuming no overflow is possible */
vinfo_t* integer_add_i(PsycoObject* po, vinfo_t* v1, long value2, bool unsafe);
EXTERNFN
vinfo_t* integer_sub  (PsycoObject* po, vinfo_t* v1, vinfo_t* v2, bool ovf);
/*EXTERNFN XXX implement me
  vinfo_t* integer_sub_i(PsycoObject* po, vinfo_t* v1, long value2);*/
EXTERNFN
vinfo_t* integer_mul  (PsycoObject* po, vinfo_t* v1, vinfo_t* v2, bool ovf);
EXTERNFN
vinfo_t* integer_mul_i(PsycoObject* po, vinfo_t* v1, long value2);
EXTERNFN
vinfo_t* integer_or   (PsycoObject* po, vinfo_t* v1, vinfo_t* v2);
EXTERNFN
vinfo_t* integer_xor  (PsycoObject* po, vinfo_t* v1, vinfo_t* v2);
EXTERNFN
vinfo_t* integer_and  (PsycoObject* po, vinfo_t* v1, vinfo_t* v2);
/*EXTERNFN
  vinfo_t* integer_and_i(PsycoObject* po, vinfo_t* v1, long value2);*/
EXTERNFN
vinfo_t* integer_lshift  (PsycoObject* po, vinfo_t* v1, vinfo_t* v2);
EXTERNFN              /* signed */
vinfo_t* integer_rshift  (PsycoObject* po, vinfo_t* v1, vinfo_t* v2);
/*EXTERNFN              unsigned
  vinfo_t* integer_urshift  (PsycoObject* po, vinfo_t* v1, vinfo_t* v2);*/
EXTERNFN
vinfo_t* integer_lshift_i(PsycoObject* po, vinfo_t* v1, long counter);
EXTERNFN              /* signed */
vinfo_t* integer_rshift_i(PsycoObject* po, vinfo_t* v1, long counter);
EXTERNFN              /* unsigned */
vinfo_t* integer_urshift_i(PsycoObject* po, vinfo_t* v1, long counter);
EXTERNFN
vinfo_t* integer_inv  (PsycoObject* po, vinfo_t* v1);
EXTERNFN
vinfo_t* integer_neg  (PsycoObject* po, vinfo_t* v1, bool ovf);
EXTERNFN
vinfo_t* integer_abs  (PsycoObject* po, vinfo_t* v1, bool ovf);
/* Comparison: 'py_op' is one of Python's rich comparison numbers
   Py_LT, Py_LE, Py_EQ, Py_NE, Py_GT, Py_GE
   optionally together with COMPARE_UNSIGNED, CHEAT_MAXINT. */
EXTERNFN condition_code_t integer_cmp  (PsycoObject* po, vinfo_t* v1,
					vinfo_t* v2, int py_op);
EXTERNFN condition_code_t integer_cmp_i(PsycoObject* po, vinfo_t* v1,
					long value2, int py_op);
#define COMPARE_UNSIGNED  8
#define CHEAT_MAXINT     16  /* assume only a constant can be exactly
                                LONG_MIN or LONG_MAX */
#define COMPARE_BASE_MASK 7
#define COMPARE_OP_MASK  15

/* Return one of two constants, depending on the condition code */
EXTERNFN vinfo_t* integer_conditional(PsycoObject* po, condition_code_t cc,
                                      long immed_true, long immed_false);

/* make a run-time copy of a vinfo_t */
EXTERNFN vinfo_t* make_runtime_copy(PsycoObject* po, vinfo_t* v);

PSY_INLINE int intlog2(long value) {
  int counter = 0;
  while ((1<<counter) < value)
    counter++;
  return counter;
}


/*****************************************************************/
 /***   code termination                                        ***/

/* write a function header reserving 'nframelocal' machine words for
   local storage. These are put in an array under LOC_CONTINUATION as
   run-time values. Do not use this with nframelocal==0; no header is
   needed (so far) in this case. */
EXTERNFN void psyco_emit_header(PsycoObject* po, int nframelocal);

/* write a return, clearing the stack as necessary, and releases 'po'.
   'retval' may not be virtual-time in the current implementation. */
EXTERNFN code_t* psyco_finish_return(PsycoObject* po, Source retval);

/* write codes that calls the C function 'fn' and jumps to its
   return value.
   Set 'restore' to 1 to save and restore all used registers across call,
   or 0 to just unload the used registers into the stack.
   This function returns a pointer to the end of the jumping code, where
   you can store closure data for 'fn'.
   The arguments that will be passed to 'fn' are:
   1) the same pointer to the closure data
   2) the run-time value described by 'extraarg' if != SOURCE_DUMMY. */
EXTERNFN
void* psyco_call_code_builder(PsycoObject* po, void* fn, int restore,
                              RunTimeSource extraarg);

#if 0   /* disabled */
/* emergency code for out-of-memory conditions in which do not
   have a code buffer available for psyco_finish_err_xxx().
   A temporary buffer of the size EMERGENCY_PROXY_SIZE is enough. */
#define EMERGENCY_PROXY_SIZE    11
code_t* psyco_emergency_jump(PsycoObject* po, code_t* code);
#endif


/*****************************************************************/
 /***   run-time switches                                       ***/

#define USE_RUNTIME_SWITCHES  0    /* DISABLED, no longer maintained */

typedef struct c_promotion_s {
  source_virtual_t header;
  int pflags;
} c_promotion_t;

#define PFlagPyObj		1
#define PFlagMegamorphic	2


#if USE_RUNTIME_SWITCHES

typedef struct fixed_switch_s {  /* private structure */
  int switchcodesize;   /* size of 'switchcode' */
  code_t* switchcode;
  int count;
  struct fxcase_s* fxc;
  long* fixtargets;
  long zero;            /* for 'array' pointers from vinfo_t structures */
  struct c_promotion_s fixed_promotion; /* pseudo-exception meaning 'fix me' */
} fixed_switch_t;

/* initialization of a fixed_switch_t structure */
EXTERNFN int psyco_build_run_time_switch(fixed_switch_t* rts, long kflags,
                                         long values[], int count);

/* Look for a (known) value in a prepared switch.
   Return -1 if not found. */
EXTERNFN int psyco_switch_lookup(fixed_switch_t* rts, long value);

/* Write the code that does a 'switch' on the prepared 'values'.
   The register 'reg' contains the value to switch on. All jump targets
   are initially at the end of the written code; see
   psyco_fix_switch_target(). */
EXTERNFN code_t* psyco_write_run_time_switch(fixed_switch_t* rts,
                                             code_t* code, reg_t reg);

/* Fix the target corresponding to the given case ('item' is a value
   returned by psyco_switch_lookup()). 'code' is the *end* of the
   switch code, as returned by psyco_write_run_time_switch(). */
EXTERNFN void psyco_fix_switch_case(fixed_switch_t* rts, code_t* code,
                                    int item, code_t* newtarget);

/* is the given run-time vinfo_t known to be none of the values
   listed in rts? */
PSY_INLINE bool known_to_be_default(vinfo_t* vi, fixed_switch_t* rts) {
	return vi->array == NullArrayAt(rts->zero);
}

#endif  /* USE_RUNTIME_SWITCHES */


/* The pseudo-exceptions meaning 'promote me' but against no particular
   fixed_switch_t. The second one has the SkFlagPyObj flag. */
EXTERNVAR c_promotion_t psyco_nonfixed_promotion;
EXTERNVAR c_promotion_t psyco_nonfixed_pyobj_promotion;

/* The same, but detecting megamorphic sites, where many different run-time
   values keep showing up.  Promotion stop after MEGAMORPHIC_MAX different
   values. */
/*EXTERNVAR c_promotion_t psyco_nonfixed_promotion_mega;*/
EXTERNVAR c_promotion_t psyco_nonfixed_pyobj_promotion_mega;

#define MEGAMORPHIC_MAX    5

/* Check if the given virtual source is a promotion exception */
EXTERNFN bool psyco_vsource_is_promotion(VirtualTimeSource source);


#endif /* _CODEGEN_H */
