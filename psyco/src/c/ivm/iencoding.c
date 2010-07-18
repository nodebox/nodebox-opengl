#include "iencoding.h"
#include "ivm-insns.h"
#include "../vcompiler.h"
#include "../dispatcher.h"
#include "../codegen.h"
#include "../codemanager.h"
#include "../Python/frames.h"


/* building run-time values meaning "the top of stack" */
#define RunTime_TOS()              RunTime_TOSF(false, false)
#define RunTime_TOSF(ref, nonneg)  RunTime_NewStack(po->stack_depth, ref, nonneg)

/* building run-time values meaning "the nth item in the stack",
   where n=0 is the top */
#define RunTime_STACK(n)           RunTime_STACKF(n, false, false)
#define RunTime_STACKF(n, ref, nonneg)                                          \
             RunTime_NewStack(po->stack_depth - (n)*sizeof(long), ref, nonneg)


DEFINEFN
void* psyco_call_code_builder(PsycoObject* po, void* fn, int restore,
			      RunTimeSource extraarg)
{
	word_t* arg;
	code_t* code = po->code;
	/* the INSN_cbuildX() instructions call the given function
	   and then jump to whatever address the function has returned. */
	if (extraarg != SOURCE_DUMMY) {
		INSN_rt_push(extraarg);
		INSN_cbuild2(&arg);
	}
	else {
		INSN_cbuild1(&arg);
	}
	*arg = (word_t) fn;
#if PSYCO_DEBUG
        /* add a zero to seperate code from data for ivmextract.py */
        *code++ = 0;
#endif
	/* make 'fs' point just after the end of the code, aligned */
	ALIGN_NO_FILL();
	return code;
}

DEFINEFN
vinfo_t* psyco_call_psyco(PsycoObject* po, CodeBufferObject* codebuf,
			  Source argsources[], int argcount,
			  struct stack_frame_info_s* finfo)
{
	word_t* arg;
	int i, initial_depth;
	Source* p;
	BEGIN_CODE
	NEED_CC();     /* 'flag' and 'retval' are a single shared register */

	ABOUT_TO_CALL_SUBFUNCTION(finfo);
	/* no stack push between the INSN_pyenter above and the INSN_vmcall
	   below, apart from function arguments! See iprocessor.c:impl_vmcall */
	initial_depth = po->stack_depth;
	p = argsources;
	for (i=argcount; i--; p++) {
		INSN_rt_push(*p); INSNPUSHED(1);
	}
	INSN_vmcall(&arg);
	*arg = (word_t) codebuf->codestart;
	po->stack_depth = initial_depth;  /* callee removes arguments */
	RETURNED_FROM_SUBFUNCTION();
	INSN_pushretval(); INSNPUSHED(1);
	END_CODE
	META_assertdepth(po->stack_depth);
	return generic_call_check(po, CfReturnRef|CfPyErrIfNull,
				  bfunction_result(po, true));
}


/***************************************************************/
 /*** Memory reads and writes                                 ***/

static void mem_access(PsycoObject* po, vinfo_t* nv_ptr,
		       long offset, vinfo_t* rt_vindex, int size2)
{
	BEGIN_CODE
	if (is_runtime(nv_ptr->source)) {
		INSN_rt_push(nv_ptr->source);
		if (offset) {
			INSN_immed(offset);
			INSN_add();
		}
	}
	else {
		offset += CompileTime_Get(nv_ptr->source)->value;
		INSN_immed(offset);
	}
	INSNPUSHED(1);
	if (rt_vindex != NULL) {
		INSN_rt_push(rt_vindex->source);
		if (size2 > 0) {
			INSN_immed(size2);
			INSN_lshift();
		}
		INSN_add();
	}
	END_CODE
}

DEFINEFN
vinfo_t* psyco_memory_read(PsycoObject* po, vinfo_t* nv_ptr,
			   long offset, vinfo_t* rt_vindex,
			   int size2, bool nonsigned)
{
	mem_access(po, nv_ptr, offset, rt_vindex, size2);
	BEGIN_CODE
	switch (size2) {
	case 0:  /* load 1 byte */
		if (nonsigned)
			INSN_load1u();
		else
			INSN_load1();
		break;
	case 1:  /* load 2 bytes */
		if (nonsigned)
			INSN_load2u();
		else
			INSN_load2();
		break;
	default: /* load 4 bytes */
		INSN_load4();
	}
	END_CODE
	return vinfo_new(RunTime_TOS());
}

DEFINEFN
bool psyco_memory_write(PsycoObject* po, vinfo_t* nv_ptr,
			long offset, vinfo_t* rt_vindex,
			int size2, vinfo_t* value)
{
	if (!compute_vinfo(value, po)) return false;
	mem_access(po, nv_ptr, offset, rt_vindex, size2);
	BEGIN_CODE
	INSN_nv_push(value->source);
	switch (size2) {
	case 0:  /* store 1 byte */
		INSN_store1();
		break;
	case 1:  /* store 2 bytes */
		INSN_store2();
		break;
	default: /* store 4 bytes */
		INSN_store4();
	}
	INSNPOPPED(1);
	END_CODE
	return true;
}


/* internal, see NEED_CC() */
EXTERNFN condition_code_t cc_from_vsource(Source source);  /* in codegen.c */

DEFINEFN
code_t* psyco_compute_cc(PsycoObject* po, code_t* code)
{
	vinfo_t* vf;
	vinfo_t* vnf;
	INSN_flag_push();
        INSNPUSHED(1);

	vf = po->ccregs[INDEX_CC(CC_FLAG)];
	vnf = po->ccregs[INDEX_CC(CC_NOT_FLAG)];
	if (vf != NULL) {
		extra_assert(cc_from_vsource(vf->source) == CC_FLAG);
		vf->source = RunTime_TOSF(false, true);
		po->ccregs[INDEX_CC(CC_FLAG)] = NULL;
	}
	if (vnf != NULL) {
		extra_assert(cc_from_vsource(vnf->source) == CC_NOT_FLAG);
		if (vf != NULL) {
			INSN_rt_push(vf->source);
			INSNPUSHED(1);
		}
		INSN_cmpz();
		INSN_flag_push();
		vnf->source = RunTime_TOSF(false, true);
		po->ccregs[INDEX_CC(CC_NOT_FLAG)] = NULL;
	}
        return code;
}

DEFINEFN
void psyco_inverted_cc(PsycoObject* po)
{
	vinfo_t* v[2];
	int i;
	for (i=0; i<2; i++) {
		v[i] = po->ccregs[i];
	}
	for (i=0; i<2; i++) {
		condition_code_t cc = (condition_code_t) i;
		if (v[i] != NULL) {
			extra_assert(cc_from_vsource(v[i]->source) == cc);
			v[i]->source = psyco_source_condition(INVERT_CC(cc));
		}
		po->ccregs[INDEX_CC(INVERT_CC(cc))] = v[i];
	}
}


/*****************************************************************/
 /***   Emit common instructions                                ***/

DEFINEFN
condition_code_t bininstrcmp(PsycoObject* po, int base_py_op,
                             vinfo_t* v1, vinfo_t* v2)
{
  condition_code_t result = CC_FLAG;
  vinfo_t* tmp;
  BEGIN_CODE
  NEED_CC();
  /* the only operation with have is '<', so exchange v1 and v2 as needed */
  switch (base_py_op & COMPARE_BASE_MASK) {
    
  case Py_NE:
    result = CC_NOT_FLAG; /* fall through */
  case Py_EQ:
    INSN_rt_push(v1->source); INSNPUSHED(1);
    INSN_rt_push(v2->source);
    INSN_cmpeq();
    goto done;
    
  case Py_LE:
    result = CC_NOT_FLAG; /* fall through */
  case Py_GT:
    tmp=v1; v1=v2; v2=tmp;
    break;
  case Py_GE:
    result = CC_NOT_FLAG;
    break;
  default:
    ;
  }
  INSN_rt_push(v1->source); INSNPUSHED(1);
  INSN_rt_push(v2->source);
  if (base_py_op & COMPARE_UNSIGNED)
    INSN_cmpltu();
  else
    INSN_cmplt();
  
 done:
  INSNPOPPED(1);
  END_CODE
  return result;
}

DEFINEFN
vinfo_t* bininstrcond(PsycoObject* po, condition_code_t cc,
		      long immed_true, long immed_false)
{
	bool swap;
	extra_assert(cc == CC_FLAG || cc == CC_NOT_FLAG);
	swap = (cc == CC_NOT_FLAG);
	BEGIN_CODE
	if (!HAS_CCREG(po)) {
		INSN_flag_push();
	}
	else {
		vinfo_t* v = po->ccregs[1];
		if (v) {
			swap = !swap;
		}
		else {
			v = po->ccregs[0];
			extra_assert(v);
		}
		code = psyco_compute_cc(po, code);
		INSN_rt_push(v->source);
	}
	if (swap) {
		long tmp = immed_true;
		immed_true = immed_false;
		immed_false = tmp;
	}
	INSN_immed(-1);
	INSN_add();
	INSN_immed(immed_false - immed_true);
	INSN_and();
	INSN_immed(immed_true);
	INSN_add();
	INSNPUSHED(1);
	END_CODE
	return vinfo_new(RunTime_TOSF(false,
				      immed_true >= 0 && immed_false >= 0));
}

#define DEFINE_BINARY_INSTRO(insn)						\
  DEFINEFN vinfo_t* bininstr##insn(PsycoObject* po, bool ovf, bool nonneg,	\
                                   vinfo_t* v1, vinfo_t* v2) {			\
    BEGIN_CODE									\
    NEED_CC();									\
    INSN_nv_push(v1->source); INSNPUSHED(1);					\
    INSN_nv_push(v2->source);							\
    INSN_##insn##_o();								\
    if (!ovf) INSN_flag_forget();						\
    END_CODE									\
    if (ovf && runtime_condition_f(po, CC_FLAG))				\
      return NULL;  /* if overflow */						\
    return vinfo_new(RunTime_TOSF(false, nonneg));				\
  }

#define DEFINE_UNARY_INSTRO(insn)						\
  DEFINEFN vinfo_t* unaryinstr##insn(PsycoObject* po, bool ovf, bool nonneg,	\
                                     vinfo_t* v1) {				\
    BEGIN_CODE									\
    NEED_CC();									\
    INSN_rt_push(v1->source); INSNPUSHED(1);					\
    INSN_##insn##_o();								\
    if (!ovf) INSN_flag_forget();						\
    END_CODE									\
    if (ovf && runtime_condition_f(po, CC_FLAG))				\
      return NULL;  /* if overflow */						\
    return vinfo_new(RunTime_TOSF(false, nonneg));				\
  }

#define DEFINE_BINARY_INSTR(insn)                                       \
  DEFINEFN vinfo_t* bininstr##insn(PsycoObject* po, bool nonneg,        \
                                   vinfo_t* v1, vinfo_t* v2) {          \
    BEGIN_CODE                                                          \
    INSN_nv_push(v1->source); INSNPUSHED(1);                            \
    INSN_nv_push(v2->source);                                           \
    INSN_##insn();                                                      \
    END_CODE                                                            \
    return vinfo_new(RunTime_TOSF(false, nonneg));                      \
  }

#define DEFINE_UNARY_INSTR(insn)                                        \
  DEFINEFN vinfo_t* unaryinstr##insn(PsycoObject* po, bool nonneg,      \
                                     vinfo_t* v1) {                     \
    BEGIN_CODE                                                          \
    INSN_rt_push(v1->source); INSNPUSHED(1);                            \
    INSN_##insn();                                                      \
    END_CODE                                                            \
    return vinfo_new(RunTime_TOSF(false, nonneg));                      \
  }

DEFINE_BINARY_INSTRO(add)
DEFINE_BINARY_INSTR(or )
DEFINE_BINARY_INSTR(and)
DEFINE_BINARY_INSTRO(sub)
DEFINE_BINARY_INSTR(xor)
DEFINE_BINARY_INSTRO(mul)
DEFINE_BINARY_INSTR(lshift)
DEFINE_BINARY_INSTR(rshift)
DEFINE_UNARY_INSTR(inv)
DEFINE_UNARY_INSTRO(neg)
DEFINE_UNARY_INSTRO(abs)

DEFINEFN
vinfo_t* bint_add_i(PsycoObject* po, vinfo_t* rt1, long value2, bool unsafe)
{
  BEGIN_CODE
  INSN_rt_push(rt1->source); INSNPUSHED(1);
  INSN_immed(value2);
  INSN_add();
  END_CODE
  return vinfo_new(RunTime_TOSF(false, unsafe &&
                                value2>=0 && is_rtnonneg(rt1->source)));
}

DEFINEFN
vinfo_t* bint_mul_i(PsycoObject* po, vinfo_t* v1, long value2, bool ovf)
{
	BEGIN_CODE
	NEED_CC();
	INSN_rt_push(v1->source); INSNPUSHED(1);
	INSN_immed(value2);
	INSN_mul_o();
	if (!ovf) INSN_flag_forget();
        END_CODE
	if (ovf && runtime_condition_f(po, CC_FLAG))
          return NULL;
	return vinfo_new(RunTime_TOSF(false,
                     ovf && value2>=0 && is_rtnonneg(v1->source)));
}

#define GENERIC_SHIFT_BY(Insn, nonneg)                  \
  {                                                     \
    extra_assert(0 < counter && counter < LONG_BIT);    \
    BEGIN_CODE                                          \
    INSN_rt_push(v1->source); INSNPUSHED(1);            \
    INSN_immed(counter);                                \
    Insn ();                                            \
    END_CODE                                            \
    return vinfo_new(RunTime_TOSF(false, nonneg));      \
  }

DEFINEFN
vinfo_t* bint_lshift_i(PsycoObject* po, vinfo_t* v1, int counter)
     GENERIC_SHIFT_BY(INSN_lshift, false)

DEFINEFN
vinfo_t* bint_rshift_i(PsycoObject* po, vinfo_t* v1, int counter)
     GENERIC_SHIFT_BY(INSN_rshift, is_nonneg(v1->source))

DEFINEFN
vinfo_t* bint_urshift_i(PsycoObject* po, vinfo_t* v1, int counter)
     GENERIC_SHIFT_BY(INSN_urshift, true)

DEFINEFN
condition_code_t bint_cmp_i(PsycoObject* po, int base_py_op,
                            vinfo_t* rt1, long immed2)
{
  condition_code_t result = CC_FLAG;
  BEGIN_CODE
  NEED_CC();
  /* the only operation with have is '<', so exchange v1 and v2 as needed */
  switch (base_py_op & COMPARE_BASE_MASK) {
    
  case Py_NE:
    result = CC_NOT_FLAG; /* fall through */
  case Py_EQ:
    INSN_rt_push(rt1->source);
    INSN_immed(immed2);
    INSN_cmpeq();
    break;
    
  case Py_LE:
    result = CC_NOT_FLAG; /* fall through */
  case Py_GT:
    INSN_immed(immed2); INSNPUSHED(1);   /* reversed arguments */
    INSN_rt_push(rt1->source);
    if (base_py_op & COMPARE_UNSIGNED)
      INSN_cmpltu();
    else
      INSN_cmplt();
    INSNPOPPED(1);
    break;
    
  case Py_GE:
    result = CC_NOT_FLAG; /* fall through */
  default:
    INSN_rt_push(rt1->source);
    INSN_immed(immed2);
    if (base_py_op & COMPARE_UNSIGNED)
      INSN_cmpltu();
    else
      INSN_cmplt();
  }
  END_CODE
  return result;
}

DEFINEFN
vinfo_t* bfunction_result(PsycoObject* po, bool ref)
{
	return vinfo_new(RunTime_TOSF(ref, false));
}

/* DEFINEFN */
/* vinfo_t* psyco_vinfo_condition(PsycoObject* po, condition_code_t cc) */
/* { */
/*   Source src; */
/*   if ((int)cc < CC_TOTAL) */
/*     { */
/*       BEGIN_CODE */
/*       INSN_flag_push(); */
/*       if (cc == CC_NOT_FLAG) */
/*         INSN_not(); */
/*       INSNPUSHED(1); */
/*       END_CODE */
/*       src = RunTime_TOSF(false, true); */
/*     } */
/*   else */
/*     src = CompileTime_New(cc == CC_ALWAYS_TRUE); */
/*   return vinfo_new(src); */
/* } */

DEFINEFN
vinfo_t* make_runtime_copy(PsycoObject* po, vinfo_t* v)
{
	if (!compute_vinfo(v, po)) return NULL;
	BEGIN_CODE
	INSN_nv_push(v->source);
	INSNPUSHED(1);
	END_CODE
	return vinfo_new(RunTime_TOSF(false, is_nonneg(v->source)));
}
