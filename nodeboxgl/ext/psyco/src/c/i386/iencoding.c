#include "iencoding.h"
#include "../vcompiler.h"
#include "../codegen.h"
#include "../dispatcher.h"
#include "../codemanager.h"
#include "../Python/frames.h"


/* We make no special use of any register but ESP, and maybe EBP
 * (if EBP_IF_RESERVED).
 * We consider that we can call C functions with arbitrary values in
 * all registers but ESP, and that only EAX, ECX and EDX will be
 * clobbered.
 * We do not use EBP as the frame pointer, unlike normal C compiled
 * functions. This makes instruction encodings one byte longer
 * (ESP-relative instead of EBP-relative).
 */

DEFINEVAR
reg_t RegistersLoop[REG_TOTAL] = {
  /* following EAX: */  REG_386_ECX,
  /* following ECX: */  REG_386_EDX,
  /* following EDX: */  REG_386_EBX,
  /* following EBX: */  EBP_IS_RESERVED ? REG_386_ESI : REG_386_EBP,
  /* following ESP: */  REG_NONE,
  /* following EBP: */  EBP_IS_RESERVED ? REG_NONE : REG_386_ESI,
  /* following ESI: */  REG_386_EDI,
  /* following EDI: */  REG_386_EAX };


#if 0   /* disabled */
DEFINEFN
code_t* psyco_emergency_jump(PsycoObject* po, code_t* code)
{
  STACK_CORRECTION(INITIAL_STACK_DEPTH - po->stack_depth);  /* at most 6 bytes */
  code[0] = 0xE9;   /* JMP rel32 */
  code += 5;
  *(long*)(code-4) = ((code_t*)(&PyErr_NoMemory)) - code;
  /* total: at most 11 bytes. Check the value of EMERGENCY_PROXY_SIZE. */
  return code;
}
#endif

DEFINEFN
void* psyco_call_code_builder(PsycoObject* po, void* fn, int restore,
                              RunTimeSource extraarg)
{
  code_t* code = po->code;
  void* result;
  code_t* fixvalue;
  #ifdef __APPLE__
  int aligndelta;
  #endif

  if (restore)
    TEMP_SAVE_REGS_FN_CALLS;
  else
    SAVE_REGS_FN_CALLS(true);

  CALL_STACK_ALIGN_DELTA(1+(extraarg != SOURCE_DUMMY), aligndelta);
  
  /* first pushed argument */
  if (extraarg != SOURCE_DUMMY)
    CALL_SET_ARG_FROM_RT(extraarg, 1, 2);  /* argument index 1 out of total 2 */
  
  /* last pushed argument (will be the first argument of 'fn') */
  code[0] = 0x68;     /* PUSH IMM32	*/
  fixvalue = code+1;    /* will be filled below */
  code[5] = 0xE8;     /* CALL fn	*/
  code += 10;
  *(long*)(code-4) = ((code_t*)fn) - code;

  if (restore)
    {
      /* cancel the effect of CALL_SET_ARG_FROM_RT on po->stack_depth,
         to match the 'ADD ESP' instruction below */
      int nb_args = 1 + (extraarg != SOURCE_DUMMY);
      po->stack_depth -= 4*(nb_args-1);
      
      extra_assert(4*nb_args < 128);   /* trivially true */
      CODE_FOUR_BYTES(code,
                      0x83,       /* ADD		  */
                      0xC4,       /*     ESP,		  */
                      4*nb_args,  /*           4*nb_args  */
                      0);         /* not used             */
      code += 3;
	  CALL_STACK_ALIGN_RESTORE(aligndelta);
      TEMP_RESTORE_REGS_FN_CALLS_AND_JUMP;
    }
  else
    {
      po->stack_depth += 4;  /* for the PUSH IMM32 above */
      code[0] = 0xFF;      /* JMP *EAX */
      code[1] = 0xE0;
      code += 2;
    }

    /* make 'fs' point just after the end of the code, aligned */
  result = (void*)(((long)code + 3) & ~ 3);
#if CODE_DUMP
  while (code != (code_t*) result)
    *code++ = (code_t) 0xCC;   /* fill with INT 3 (debugger trap) instructions */
#endif
  *(void**)fixvalue = result;    /* set value at code+1 above */
  return result;
}

DEFINEFN
vinfo_t* psyco_call_psyco(PsycoObject* po, CodeBufferObject* codebuf,
			  Source argsources[], int argcount,
			  struct stack_frame_info_s* finfo)
{
	/* this is a simplified version of psyco_generic_call() which
	   assumes Psyco's calling convention instead of the C's. */
	int i, initial_depth;
	Source* p;
	bool ccflags;
	#ifdef __APPLE__
	int aligncount=0;
	#endif
	BEGIN_CODE
	/* cannot use NEED_CC(): it might clobber one of the registers
	   mentioned in argsources */
        ccflags = HAS_CCREG(po);
    #ifdef __APPLE__
	/* Calculate number of registers that will be pushed by
	   NEED_REGISTER */
	for (i=0; i<REG_TOTAL; i++)
	{
		vinfo_t* _content = REG_NUMBER(po, i);
		if (_content != NULL)
			if (RUNTIME_STACK(_content) == RUNTIME_STACK_NONE)
				aligncount++;
	}
	#endif
	CALL_STACK_ALIGN(1+(ccflags!=0)+aligncount);
	if (ccflags)
		PUSH_CC_FLAGS();
	for (i=0; i<REG_TOTAL; i++)
		NEED_REGISTER(i);
	finfo_last(finfo)->link_stack_depth = po->stack_depth;
	ABOUT_TO_CALL_SUBFUNCTION(finfo);
	initial_depth = po->stack_depth;
	CALL_SET_ARG_IMMED(-1, argcount, argcount+1);
	p = argsources;
	for (i=argcount; i--; p++)
		CALL_SET_ARG_FROM_RT(*p, i, argcount+1);
	CALL_C_FUNCTION(codebuf->codestart, argcount+1);
	po->stack_depth = initial_depth;  /* callee removes arguments */
	RETURNED_FROM_SUBFUNCTION();
	if (ccflags)
		POP_CC_FLAGS();
	END_CODE
	return generic_call_check(po, CfReturnRef|CfPyErrIfNull,
				  bfunction_result(po, true));
}


/* run-time vinfo_t creation */
PSY_INLINE vinfo_t* new_rtvinfo(PsycoObject* po, reg_t reg, bool ref, bool nonneg) {
	vinfo_t* vi = vinfo_new(RunTime_New(reg, ref, nonneg));
	REG_NUMBER(po, reg) = vi;
	return vi;
}

PSY_INLINE code_t* write_modrm(code_t* code, code_t middle,
                           reg_t base, reg_t index, int shift,
                           unsigned long offset)
{
  /* write a mod/rm encoding. */
  extra_assert(index != REG_386_ESP);
  extra_assert(0 <= shift && shift < 4);
  if (base == REG_NONE)
    {
      if (index == REG_NONE)
        {
          code[0] = middle | 0x05;
          *(unsigned long*)(code+1) = offset;
          return code+5;
        }
      else
        {
          code[0] = middle | 0x04;
          code[1] = (shift<<6) | (index<<3) | 0x05;
          *(unsigned long*)(code+2) = offset;
          return code+6;
        }
    }
  else if (index == REG_NONE)
    {
      if (base == REG_386_ESP)
        {
          code[0] = 0x84 | middle;
          code[1] = 0x24;
          *(unsigned long*)(code+2) = offset;
          return code+6;
        }
      else if (COMPACT_ENCODING && offset == 0 && base!=REG_386_EBP)
        {
          code[0] = middle | base;
          return code+1;
        }
      else if (COMPACT_ENCODING && offset < 128)
        {
          code[0] = 0x40 | middle | base;
          code[1] = (code_t) offset;
          return code+2;
        }
      else
        {
          code[0] = 0x80 | middle | base;
          *(unsigned long*)(code+1) = offset;
          return code+5;
        }
    }
  else
    {
      code[1] = (shift<<6) | (index<<3) | base;
      if (COMPACT_ENCODING && offset == 0 && base!=REG_386_EBP)
        {
          code[0] = middle | 0x04;
          return code+2;
        }
      else if (COMPACT_ENCODING && offset < 128)
        {
          code[0] = middle | 0x44;
          code[2] = (code_t) offset;
          return code+3;
        }
      else
        {
          code[0] = middle | 0x84;
          *(long*)(code+2) = offset;
          return code+6;
        }
    }
}

#define NewOutputRegister  ((vinfo_t*) 1)

static reg_t mem_access(PsycoObject* po, code_t opcodes[], vinfo_t* nv_ptr,
                        long offset, vinfo_t* rt_vindex, int size2,
                        vinfo_t* rt_extra)
{
  int i;
  reg_t basereg, indexreg, extrareg;

  BEGIN_CODE
  if (is_runtime(nv_ptr->source))
    {
      RTVINFO_IN_REG(nv_ptr);
      basereg = RUNTIME_REG(nv_ptr);
    }
  else
    {
      offset += CompileTime_Get(nv_ptr->source)->value;
      basereg = REG_NONE;
    }
  
  if (rt_vindex != NULL)
    {
      DELAY_USE_OF(basereg);
      RTVINFO_IN_REG(rt_vindex);
      indexreg = RUNTIME_REG(rt_vindex);
    }
  else
    indexreg = REG_NONE;

  if (rt_extra == NULL)
    extrareg = 0;
  else
    {
      DELAY_USE_OF_2(basereg, indexreg);
      if (rt_extra == NewOutputRegister)
        NEED_FREE_REG(extrareg);
      else
        {
          if (size2==0)
            RTVINFO_IN_BYTE_REG(rt_extra, basereg, indexreg);
          else
            RTVINFO_IN_REG(rt_extra);
          extrareg = RUNTIME_REG(rt_extra);
        }
    }
  
  for (i = *opcodes++; i--; ) *code++ = *opcodes++;
  code = write_modrm(code, (code_t)(extrareg<<3), basereg, indexreg, size2,
                     (unsigned long) offset);
  for (i = *opcodes++; i--; ) *code++ = *opcodes++;
  END_CODE
  return extrareg;
}

DEFINEFN
vinfo_t* psyco_memory_read(PsycoObject* po, vinfo_t* nv_ptr, long offset,
                           vinfo_t* rt_vindex, int size2, bool nonsigned)
{
  code_t opcodes[4];
  reg_t targetreg;
  switch (size2) {
  case 0:
    /* reading only one byte */
    opcodes[0] = 2;
    opcodes[1] = 0x0F;
    opcodes[2] = nonsigned
      ? 0xB6       /* MOVZX reg, byte [...] */
      : 0xBE;      /* MOVSX reg, byte [...] */
    opcodes[3] = 0;
    break;
  case 1:
    /* reading only two bytes */
    opcodes[0] = 2;
    opcodes[1] = 0x0F;
    opcodes[2] = nonsigned
      ? 0xB7       /* MOVZX reg, short [...] */
      : 0xBF;      /* MOVSX reg, short [...] */
    opcodes[3] = 0;
    break;
  default:
    /* reading a long */
    opcodes[0] = 1;
    opcodes[1] = 0x8B;  /* MOV reg, long [...] */
    opcodes[2] = 0;
    break;
  }
  targetreg = mem_access(po, opcodes, nv_ptr, offset, rt_vindex,
                         size2, NewOutputRegister);
  return new_rtvinfo(po, targetreg, false, false);
}

DEFINEFN
bool psyco_memory_write(PsycoObject* po, vinfo_t* nv_ptr, long offset,
                        vinfo_t* rt_vindex, int size2, vinfo_t* value)
{
  code_t opcodes[8];
  if (!compute_vinfo(value, po)) return false;

  if (is_runtime(value->source))
    {
      switch (size2) {
      case 0:
        /* writing only one byte */
        opcodes[0] = 1;
        opcodes[1] = 0x88;   /* MOV byte [...], reg */
        /* 'reg' is forced in mem_access to be an 8-bit register */
        opcodes[2] = 0;
        break;
      case 1:
        /* writing only two bytes */
        opcodes[0] = 2;
        opcodes[1] = 0x66;
        opcodes[2] = 0x89;   /* MOV short [...], reg */
        opcodes[3] = 0;
        break;
      default:
        /* writing a long */
        opcodes[0] = 1;
        opcodes[1] = 0x89;   /* MOV long [...], reg */
        opcodes[2] = 0;
        break;
      }
    }
  else
    {
      code_t* code1;
      long immed = CompileTime_Get(value->source)->value;
      value = NULL;  /* not run-time */
      switch (size2) {
      case 0:
        /* writing an immediate byte */
        opcodes[0] = 1;
        opcodes[1] = 0xC6;
        opcodes[2] = 1;
        opcodes[3] = (code_t) immed;
        break;
      case 1:
        /* writing an immediate short */
        opcodes[0] = 2;
        opcodes[1] = 0x66;
        opcodes[2] = 0xC7;
        opcodes[3] = 2;
        opcodes[4] = (code_t) immed;
        opcodes[5] = (code_t) (immed >> 8);
        break;
      default:
        /* writing an immediate long */
        code1 = opcodes;  /* workaround for a GCC overoptimization */
        code1[0] = 1;
        code1[1] = 0xC7;
        code1[2] = 4;
        *(long*)(code1+3) = immed;
        break;
      }
    }
  mem_access(po, opcodes, nv_ptr, offset, rt_vindex, size2, value);
  return true;
}


/* internal, see NEED_CC() */
EXTERNFN condition_code_t cc_from_vsource(Source source);  /* in codegen.c */

DEFINEFN
code_t* psyco_compute_cc(PsycoObject* po, code_t* code, reg_t reserved)
{
	int i;
	vinfo_t* v;
	condition_code_t cc;
	reg_t rg;
	for (i=0; i<2; i++) {
		v = po->ccregs[i];
		if (v == NULL)
			continue;
		cc = cc_from_vsource(v->source);

		NEED_FREE_BYTE_REG(rg, reserved, REG_NONE);
		LOAD_REG_FROM_CONDITION(rg, cc);

		v->source = RunTime_New(rg, false, true);
		REG_NUMBER(po, rg) = v;
		po->ccregs[i] = NULL;
	}
        return code;
}


/*****************************************************************/
 /***   Emit common instructions                                ***/


DEFINEFN
vinfo_t* bininstrgrp(PsycoObject* po, int group, bool ovf, bool nonneg,
                     vinfo_t* v1, vinfo_t* v2)
{
  reg_t rg;
  BEGIN_CODE
  NEED_CC();
  COPY_IN_REG(v1, rg);                      /* MOV rg, (v1) */
  COMMON_INSTR_FROM(group, rg, v2->source); /* XXX rg, (v2) */
  END_CODE
  if (ovf && runtime_condition_f(po, CC_O))
    return NULL;  /* if overflow */
  return new_rtvinfo(po, rg, false, nonneg);
}

DEFINEFN
vinfo_t* bint_add_i(PsycoObject* po, vinfo_t* rt1, long value2, bool unsafe)
{
  reg_t rg, dst;
  extra_assert(is_runtime(rt1->source));
  BEGIN_CODE
  NEED_FREE_REG(dst);
  rg = getreg(rt1->source);
  if (rg == REG_NONE)
    {
      rg = dst;
      LOAD_REG_FROM(rt1->source, rg);
    }
  LOAD_REG_FROM_REG_PLUS_IMMED(dst, rg, value2);
  END_CODE
  return new_rtvinfo(po, dst, false,
		unsafe && value2>=0 && is_rtnonneg(rt1->source));
}

#define GENERIC_SHIFT_BY(rtmacro, nonneg)               \
  {                                                     \
    reg_t rg;                                           \
    extra_assert(0 < counter && counter < LONG_BIT);    \
    BEGIN_CODE                                          \
    NEED_CC();                                          \
    COPY_IN_REG(v1, rg);                                \
    rtmacro(rg, counter);                               \
    END_CODE                                            \
    return new_rtvinfo(po, rg, false, nonneg);          \
  }

DEFINEFN
vinfo_t* bininstrshift(PsycoObject* po, int group,
                       bool nonneg, vinfo_t* v1, vinfo_t* v2)
{
  reg_t rg;
  BEGIN_CODE
  if (RSOURCE_REG(v2->source) != SHIFT_COUNTER) {
    NEED_REGISTER(SHIFT_COUNTER);
    LOAD_REG_FROM(v2->source, SHIFT_COUNTER);
  }
  NEED_CC_REG(SHIFT_COUNTER);
  DELAY_USE_OF(SHIFT_COUNTER);
  COPY_IN_REG(v1, rg);
  SHIFT_GENERICCL(rg, group);      /* SHx rg, CL */
  END_CODE
  return new_rtvinfo(po, rg, false, nonneg);
}


DEFINEFN
vinfo_t* bint_lshift_i(PsycoObject* po, vinfo_t* v1, int counter)
     GENERIC_SHIFT_BY(SHIFT_LEFT_BY, false)

DEFINEFN
vinfo_t* bint_rshift_i(PsycoObject* po, vinfo_t* v1, int counter)
     GENERIC_SHIFT_BY(SHIFT_SIGNED_RIGHT_BY, is_nonneg(v1->source))

DEFINEFN
vinfo_t* bint_urshift_i(PsycoObject* po, vinfo_t* v1, int counter)
     GENERIC_SHIFT_BY(SHIFT_RIGHT_BY, true)

DEFINEFN
vinfo_t* bint_mul_i(PsycoObject* po, vinfo_t* v1, long value2, bool ovf)
{
  reg_t rg;
  BEGIN_CODE
  NEED_CC();
  NEED_FREE_REG(rg);
  IMUL_IMMED_FROM_RT(v1->source, value2, rg);
  END_CODE
  if (ovf && runtime_condition_f(po, CC_O))
    return NULL;
  return new_rtvinfo(po, rg, false,
                     ovf && value2>=0 && is_rtnonneg(v1->source));
}

DEFINEFN
vinfo_t* bininstrmul(PsycoObject* po, bool ovf,
                     bool nonneg, vinfo_t* v1, vinfo_t* v2)
{
  reg_t rg;
  BEGIN_CODE
  NEED_CC();
  COPY_IN_REG(v1, rg);               /* MOV rg, (v1) */
  IMUL_REG_FROM_RT(v2->source, rg);  /* IMUL rg, (v2) */
  END_CODE
  if (ovf && runtime_condition_f(po, CC_O))
    return NULL;  /* if overflow */
  return new_rtvinfo(po, rg, false, nonneg);
}

DEFINEFN
vinfo_t* unaryinstrgrp(PsycoObject* po, int group, bool ovf,
                       bool nonneg, vinfo_t* v1)
{
  reg_t rg;
  BEGIN_CODE
  NEED_CC();
  COPY_IN_REG(v1, rg);                  /* MOV rg, (v1) */
  UNARY_INSTR_ON_REG(group, rg);        /* XXX rg       */
  END_CODE
  if (ovf && runtime_condition_f(po, CC_O))
    return NULL;  /* if overflow */
  return new_rtvinfo(po, rg, false, nonneg);
}

DEFINEFN
vinfo_t* unaryinstrabs(PsycoObject* po, bool ovf,
                                bool nonneg, vinfo_t* v1)
{
  reg_t rg;
  BEGIN_CODE
  NEED_CC();
  COPY_IN_REG(v1, rg);                  /*  MOV  rg, (v1) */
  INT_ABS(rg, v1->source);              /* 'ABS' rg       */
  END_CODE
  if (ovf && runtime_condition_f(po, CHECK_ABS_OVERFLOW))
    return NULL;  /* if overflow */
  return new_rtvinfo(po, rg, false, nonneg);
}

static const condition_code_t direct_results[16] = {
	  /*****   signed comparison      **/
          /* Py_LT: */  CC_L,
          /* Py_LE: */  CC_LE,
          /* Py_EQ: */  CC_E,
          /* Py_NE: */  CC_NE,
          /* Py_GT: */  CC_G,
          /* Py_GE: */  CC_GE,
	  /* (6)    */  CC_ERROR,
	  /* (7)    */  CC_ERROR,
	  /*****  unsigned comparison     **/
          /* Py_LT: */  CC_uL,
          /* Py_LE: */  CC_uLE,
          /* Py_EQ: */  CC_E,
          /* Py_NE: */  CC_NE,
          /* Py_GT: */  CC_uG,
          /* Py_GE: */  CC_uGE,
	  /* (14)   */  CC_ERROR,
	  /* (15)   */  CC_ERROR };

DEFINEFN
condition_code_t bint_cmp_i(PsycoObject* po, int base_py_op,
                            vinfo_t* rt1, long immed2)
{
  BEGIN_CODE
  NEED_CC();
  COMPARE_IMMED_FROM_RT(rt1->source, immed2); /* CMP rt1, immed2 */
  END_CODE
  return direct_results[base_py_op];
}

DEFINEFN
condition_code_t bininstrcmp(PsycoObject* po, int base_py_op,
                             vinfo_t* v1, vinfo_t* v2)
{
  BEGIN_CODE
  NEED_CC();
  RTVINFO_IN_REG(v1);         /* CMP v1, v2 */
  COMMON_INSTR_FROM_RT(7, getreg(v1->source), v2->source);
  END_CODE
  return direct_results[base_py_op];
}

DEFINEFN
vinfo_t* bininstrcond(PsycoObject* po, condition_code_t cc,
                      long immed_true, long immed_false)
{
  reg_t rg;
  BEGIN_CODE
  NEED_FREE_REG(rg);
  LOAD_REG_FROM_IMMED(rg, immed_true);
  SHORT_COND_JUMP_TO(code + SIZE_OF_SHORT_CONDITIONAL_JUMP
                          + SIZE_OF_LOAD_REG_FROM_IMMED, cc);
  LOAD_REG_FROM_IMMED(rg, immed_false);
  END_CODE
  return new_rtvinfo(po, rg, false, immed_true >= 0 && immed_false >= 0);
}

DEFINEFN
vinfo_t* bfunction_result(PsycoObject* po, bool ref)
{
  return new_rtvinfo(po, REG_FUNCTIONS_RETURN, ref, false);
}

DEFINEFN
vinfo_t* make_runtime_copy(PsycoObject* po, vinfo_t* v)
{
	reg_t rg;
	if (!compute_vinfo(v, po)) return NULL;
	BEGIN_CODE
	NEED_FREE_REG(rg);
	LOAD_REG_FROM(v->source, rg);
	END_CODE
	return new_rtvinfo(po, rg, false, is_nonneg(v->source));
}


#if 0
DEFINEFN   -- unused --
vinfo_t* integer_and_i(PsycoObject* po, vinfo_t* v1, long value2)
     GENERIC_BINARY_INSTR_2(4, a & b,    /* AND */
			    value2>=0 || is_rtnonneg(v1->source))
#define GENERIC_BINARY_INSTR_2(group, c_code, nonneg)                   \
{                                                                       \
  if (!compute_vinfo(v1, po)) return NULL;                              \
  if (is_compiletime(v1->source))                                       \
    {                                                                   \
      long a = CompileTime_Get(v1->source)->value;                      \
      long b = value2;                                                  \
      long c = (c_code);                                                \
      return vinfo_new(CompileTime_New(c));                             \
    }                                                                   \
  else                                                                  \
    {                                                                   \
      reg_t rg;                                                         \
      BEGIN_CODE                                                        \
      NEED_CC();                                                        \
      COPY_IN_REG(v1, rg);                   /* MOV rg, (v1) */         \
      COMMON_INSTR_IMMED(group, rg, value2); /* XXX rg, value2 */       \
      END_CODE                                                          \
      return new_rtvinfo(po, rg, false, nonneg);                        \
    }                                                                   \
}
#endif

#if 0
DEFINEFN      (not used)
vinfo_t* integer_seqindex(PsycoObject* po, vinfo_t* vi, vinfo_t* vn, bool ovf)
{
  NonVirtualSource vns, vis;
  vns = vinfo_compute(vn, po);
  if (vns == SOURCE_ERROR) return NULL;
  vis = vinfo_compute(vi, po);
  if (vis == SOURCE_ERROR) return NULL;
  
  if (!is_compiletime(vis))
    {
      reg_t rg, tmprg;
      BEGIN_CODE
      NEED_CC_SRC(vis);
      NEED_FREE_REG(rg);
      LOAD_REG_FROM_RT(vis, rg);
      DELAY_USE_OF(rg);
      NEED_FREE_REG(tmprg);

      /* Increase 'rg' by 'vns' unless it is already in the range(0, vns). */
         /* CMP i, n */
      vns = vn->source;  /* reload, could have been moved by NEED_FREE_REG */
      COMMON_INSTR_FROM(7, rg, vns);
         /* SBB t, t */
      COMMON_INSTR_FROM_RT(3, tmprg, RunTime_New(tmprg, false...));
         /* AND t, n */
      COMMON_INSTR_FROM(4, tmprg, vns);
         /* SUB i, t */
      COMMON_INSTR_FROM_RT(5, rg, RunTime_New(tmprg, false...));
         /* ADD i, n */
      COMMON_INSTR_FROM(0, rg, vns);
      END_CODE

      if (ovf && runtime_condition_f(po, CC_NB))  /* if out of range */
        return NULL;
      return new_rtvinfo(po, rg, false...);
    }
  else
    {
      long index = CompileTime_Get(vis)->value;
      long reqlength;
      if (index >= 0)
        reqlength = index;  /* index is known, length must be greater than it */
      else
        reqlength = ~index;  /* idem for negative index */
      if (ovf)
        {
          /* test for out of range index -- more precisely, test that the
             length is not large enough for the known index */
          condition_code_t cc = integer_cmp_i(po, vn, reqlength, Py_LE);
          if (cc == CC_ERROR || runtime_condition_f(po, cc))
            return NULL;
        }
      if (index >= 0)
        {
          vinfo_incref(vi);
          return vi;
        }
      else
        return integer_add_i(po, vn, index...);
    }
}
#endif  /* 0 */
