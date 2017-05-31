 /***************************************************************/
/***       Processor-specific code-producing macros            ***/
 /***************************************************************/


#ifndef _IENCODING_H
#define _IENCODING_H


#include "../psyco.h"
#define MACHINE_CODE_FORMAT    "ivm"
#define HAVE_FP_FN_CALLS       0


#define REG_TOTAL   0           /* the virtual machine has only a stack */

/* the condition code is stored in the 'flag' register. */
typedef enum {
	CC_FLAG      = 0,
        CC_NOT_FLAG  = 1,
#define CC_TOTAL       2
        CC_ALWAYS_FALSE  = 2,   /* pseudo condition codes for known outcomes */
        CC_ALWAYS_TRUE   = 3,
        CC_ERROR         = -1 } condition_code_t;

#define INVERT_CC(cc)    ((condition_code_t)((int)(cc) ^ 1))
#define HAVE_CCREG       2
#define INDEX_CC(cc)     (extra_assert((cc) == CC_FLAG || (cc) == CC_NOT_FLAG), \
                          (int)(cc))
#define HAS_CCREG(po)    ((po)->ccregs[0] != NULL || (po)->ccregs[1] != NULL)

#if PSYCO_DEBUG
struct cc_s;
# define CC_FLAG          ((struct cc_s*) CC_FLAG)
# define CC_NOT_FLAG      ((struct cc_s*) CC_NOT_FLAG)
# define CC_ALWAYS_FALSE  ((struct cc_s*) CC_ALWAYS_FALSE)
# define CC_ALWAYS_TRUE   ((struct cc_s*) CC_ALWAYS_TRUE)
# define CC_ERROR         ((struct cc_s*) CC_ERROR)
# define condition_code_t   struct cc_s*
#endif


/* processor-depend part of PsycoObject */
#define PROCESSOR_PSYCOOBJECT_FIELDS                                            \
	int stack_depth;   /* the size of data currently pushed in the stack */ \
        int minimal_stack_size;   /* total stack size that we are sure about */ \
	vinfo_t* ccregs[2];       /* processor condition codes (aka flags)  */
#define INIT_PROCESSOR_PSYCOOBJECT(po)           \
          ((po)->minimal_stack_size = VM_INITIAL_MINIMAL_STACK_SIZE)

#define PROCESSOR_FROZENOBJECT_FIELDS                                           \
	unsigned short minimal_extra_stack_words;   /* ~= minimal_stack_size */
#define SAVE_PROCESSOR_FROZENOBJECT(fpo, po)     do {			\
	int extra_stack_words = ((po)->minimal_stack_size -		\
				 (po)->stack_depth) / sizeof(long);	\
	if (extra_stack_words < 0)					\
		extra_stack_words = 0;					\
	else if (extra_stack_words > 0xFFFF)				\
		extra_stack_words = 0xFFFF;				\
	(fpo)->minimal_extra_stack_words = extra_stack_words;		\
} while (0)
#define RESTORE_PROCESSOR_FROZENOBJECT(fpo, po)  do {			\
	(po)->minimal_stack_size = (po)->stack_depth +			\
		(fpo)->minimal_extra_stack_words * sizeof(long);	\
} while (0)

#define CHECK_STACK_SPACE()      do {						\
	if (po->stack_depth >= po->minimal_stack_size) {			\
		BEGIN_CODE							\
		INSN_stackgrow();						\
		END_CODE							\
		po->minimal_stack_size = po->stack_depth + VM_EXTRA_STACK_SIZE;	\
        }									\
	META_assertdepth(po->stack_depth);					\
} while(0)


#define CURRENT_STACK_POSITION(rtsource)  (                             \
        (po->stack_depth - getstack(rtsource)) / sizeof(long))

/* release a run-time vinfo_t */
/* #define RTVINFO_RELEASE(rtsource)       do {				\ */
/* 	// pop an item off the stack only if it is close to the top   	\ */
/* 	switch (CURRENT_STACK_POSITION(rtsource)) {			\ */
/* 	case 0:								\ */
/* 		INSN_pop(); INSN_POPPED(1);				\ */
/* 		break;							\ */
/* 	case 1:								\ */
/* 		INSN_pop2nd(); ???					\ */
/* 		break;							\ */
/* 	default:							\ */
/* 		break;  // not removed					\ */
/* 	}								\ */
/* } while (0) */
#define RTVINFO_RELEASE(rtsource)   do { /* nothing */ } while (0)

/* move a run-time vinfo_t */
#define RTVINFO_MOVE(rtsource, vtarget)   do { /*nothing*/ } while (0)

/* for PsycoObject_Duplicate() */
#define DUPLICATE_PROCESSOR(result, po)   do {				\
	int i;								\
	result->stack_depth = po->stack_depth;				\
	result->minimal_stack_size = po->minimal_stack_size;		\
	for (i=0; i<2; i++)                                   		\
		if (po->ccregs[i] != NULL)                          	\
			result->ccregs[i] = po->ccregs[i]->tmp;		\
} while (0)

#define RTVINFO_CHECK(po, vsource, found) do { /*nothing*/ } while (0)
#define RTVINFO_CHECKED(po, found)        do { /*nothing*/ } while (0)

#define ABOUT_TO_CALL_SUBFUNCTION(finfo)  do {  \
  word_t* _arg;                                 \
  INSN_pyenter(&_arg);                          \
  *_arg = (word_t)(finfo);                      \
} while (0)
#define RETURNED_FROM_SUBFUNCTION()       do {  \
  INSN_pyleave();                               \
} while (0)


/*****************************************************************/
 /***   Emit common instructions                                ***/

#define EXTERN_BINARY_INSTRO(insn)                                              \
  EXTERNFN vinfo_t* bininstr##insn(PsycoObject* po, bool ovf, bool nonneg,      \
                                   vinfo_t* v1, vinfo_t* v2);
#define EXTERN_UNARY_INSTRO(insn)                                               \
  EXTERNFN vinfo_t* unaryinstr##insn(PsycoObject* po, bool ovf, bool nonneg,    \
                                     vinfo_t* v1);
#define EXTERN_BINARY_INSTR(insn)                                               \
  EXTERNFN vinfo_t* bininstr##insn(PsycoObject* po, bool nonneg,                \
                                   vinfo_t* v1, vinfo_t* v2);
#define EXTERN_UNARY_INSTR(insn)                                                \
  EXTERNFN vinfo_t* unaryinstr##insn(PsycoObject* po, bool nonneg,              \
                                     vinfo_t* v1);

EXTERN_BINARY_INSTRO(add)
EXTERN_BINARY_INSTR (or)
EXTERN_BINARY_INSTR (and)
EXTERN_BINARY_INSTRO(sub)
EXTERN_BINARY_INSTR (xor)
EXTERN_BINARY_INSTRO(mul)
EXTERN_BINARY_INSTR (lshift)
EXTERN_BINARY_INSTR (rshift)
EXTERN_UNARY_INSTR  (inv)
EXTERN_UNARY_INSTRO (neg)
EXTERN_UNARY_INSTRO (abs)

EXTERNFN condition_code_t bininstrcmp(PsycoObject* po, int base_py_op,
                                      vinfo_t* v1, vinfo_t* v2);
EXTERNFN vinfo_t* bininstrcond(PsycoObject* po, condition_code_t cc,
                               long immed_true, long immed_false);

#define BINARY_INSTR_ADD(ovf, nonneg)  bininstradd(po,     ovf,   nonneg, v1, v2)
#define BINARY_INSTR_OR( ovf, nonneg)  bininstror (po,            nonneg, v1, v2)
#define BINARY_INSTR_AND(ovf, nonneg)  bininstrand(po,            nonneg, v1, v2)
#define BINARY_INSTR_SUB(ovf, nonneg)  bininstrsub(po,     ovf,   nonneg, v1, v2)
#define BINARY_INSTR_XOR(ovf, nonneg)  bininstrxor(po,            nonneg, v1, v2)
#define BINARY_INSTR_MUL(ovf, nonneg)  bininstrmul(po,     ovf,   nonneg, v1, v2)
#define BINARY_INSTR_LSHIFT(  nonneg)  bininstrlshift(po,         nonneg, v1, v2)
#define BINARY_INSTR_RSHIFT(  nonneg)  bininstrrshift(po,         nonneg, v1, v2)
#define BINARY_INSTR_CMP(base_py_op)   bininstrcmp(po, base_py_op,  v1, v2)
#define BINARY_INSTR_COND(cc, i1, i2)  bininstrcond(po, cc,         i1, i2)
#define UNARY_INSTR_INV(ovf,  nonneg)  unaryinstrinv(po,      nonneg, v1)
#define UNARY_INSTR_NEG(ovf,  nonneg)  unaryinstrneg(po, ovf, nonneg, v1)
#define UNARY_INSTR_ABS(ovf,  nonneg)  unaryinstrabs(po, ovf, nonneg, v1)

EXTERNFN vinfo_t* bint_add_i(PsycoObject* po, vinfo_t* rt1, long value2,
                             bool unsafe);
EXTERNFN vinfo_t* bint_mul_i(PsycoObject* po, vinfo_t* v1, long value2,
                             bool ovf);
EXTERNFN vinfo_t* bint_lshift_i(PsycoObject* po, vinfo_t* v1, int counter);
EXTERNFN vinfo_t* bint_rshift_i(PsycoObject* po, vinfo_t* v1, int counter);
EXTERNFN vinfo_t* bint_urshift_i(PsycoObject* po, vinfo_t* v1, int counter);
EXTERNFN condition_code_t bint_cmp_i(PsycoObject* po, int base_py_op,
                                     vinfo_t* rt1, long immed2);
EXTERNFN vinfo_t* bfunction_result(PsycoObject* po, bool ref);

/***************************************************************/
 /***   some macro for code emission                          ***/

#define CHECK_NONZERO_FROM_RT(src, rcc)   do {                          \
	NEED_CC();                                                      \
	INSN_rt_push(src);                                              \
	INSN_cmpz();  /* negative form, to normalize to 1 or 0 */       \
	rcc = CC_NOT_FLAG;                                              \
} while (0)

#define NEED_CC()   do {                        \
  if (HAS_CCREG(po))                            \
    code = psyco_compute_cc(po, code);          \
} while (0)
/* internal */
EXTERNFN code_t* psyco_compute_cc(PsycoObject* po, code_t* code);
EXTERNFN void psyco_inverted_cc(PsycoObject* po);

#define SAVE_REGS_FN_CALLS(cc)        do { if (cc) NEED_CC(); } while (0)

#define TEMP_SAVE_REGS_FN_CALLS       do { /* nothing */ } while (0)

#define TEMP_RESTORE_REGS_FN_CALLS    do { /* nothing */ } while (0)

#define JUMP_TO(target)               do {      \
  word_t* _arg;                                 \
  INSN_jumpfar(&_arg);                          \
  *_arg = (word_t) target;                      \
} while (0)

#define MAXIMUM_SIZE_OF_FAR_JUMP  (sizeof(code_t)+sizeof(word_t)+sizeof(code_t))


#define CALL_SET_ARG_IMMED(immed, arg_index, nb_args)     do {  \
  INSN_immed(immed);                                            \
  INSNPUSHED(1);                                                \
} while (0)
#define CALL_SET_ARG_FROM_RT(source, arg_index, nb_args)  do {  \
  INSN_rt_push(source);                                         \
  INSNPUSHED(1);                                                \
} while (0)
#define CALL_SET_ARG_FROM_ADDR(source, arg_index, nb_args) do { \
  INSN_ref_push(CURRENT_STACK_POSITION(source));                \
  INSNPUSHED(1);                                                \
} while (0)
#define CALL_C_FUNCTION(target, nb_args)   do {                         \
  word_t* _arg;                                                         \
  switch (nb_args) {                                                    \
  case 0: INSN_ccall0(&_arg); break;                                    \
  case 1: INSN_ccall1(&_arg); break;                                    \
  case 2: INSN_ccall2(&_arg); break;                                    \
  case 3: INSN_ccall3(&_arg); break;                                    \
  case 4: INSN_ccall4(&_arg); break;                                    \
  case 5: INSN_ccall5(&_arg); break;                                    \
  case 6: INSN_ccall6(&_arg); break;                                    \
  case 7: INSN_ccall7(&_arg); break;                                    \
  default: psyco_fatal_msg("too many arguments to C function call");    \
  }                                                                     \
  *_arg = (word_t)(target);                                             \
  INSNPOPPED((nb_args)-1);  /* can be -1, if nb_args is 0 */            \
} while (0)


#define STACK_CORRECTION(stack_correction)   do {       \
  int _stackcorr = (int)(stack_correction);             \
  if (_stackcorr < 0)                                   \
    INSN_settos((-_stackcorr) / sizeof(long));          \
  else if (_stackcorr > 0)                              \
    INSN_pushn(_stackcorr / sizeof(long));              \
} while (0)
/* Dummy stack alignment for non-MacOS X */
#define CALL_STACK_ALIGN_DELTA(nbargs, delta)
#define CALL_STACK_ALIGN(nbargs)
#define CALL_STACK_ALIGN_RESTORE(delta)

#define FUNCTION_RET(popbytes)      do {                                        \
  INSN_ret((popbytes) / sizeof(long) + 1);   /* +1 for the retaddr itself */    \
} while (0)

#if defined(PSYCO_TRACE)
# error "This Trace not implemented for the ivm; use IVM_TRACE instead"
#endif


#define ALIGN_CODE_MASK  (sizeof(long)-1)

#define ALIGN_PAD_CODE_PTR()     do {                                           \
  code = (code_t*)((((long)code) + ALIGN_CODE_MASK) & ~ALIGN_CODE_MASK);        \
} while (0)

#define ALIGN_WITH_BYTE(byte)    do {           \
  while (((long)code) & ALIGN_CODE_MASK)        \
    *code++ = byte;                             \
} while (0)

#define ALIGN_WITH_NOP()         do { /*nothing*/ } while (0)

#if ALL_CHECKS
#define ALIGN_NO_FILL() ALIGN_WITH_BYTE(0xFF)   /* debugging */
#else
#define ALIGN_NO_FILL() ALIGN_PAD_CODE_PTR()
#endif


#endif /* _IENCODING_H */
