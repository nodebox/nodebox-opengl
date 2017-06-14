#include "codegen.h"
#include "codemanager.h"
#include "Python/frames.h"
#include "Python/pycompiler.h"
#include <iencoding.h>
#include "pycodegen.h"

/*** The processor-independent part of the code generator. ***/


DEFINEFN
void psyco_emit_header(PsycoObject* po, int nframelocal)
{
  int j = nframelocal;
  vinfo_array_t* array;
  extra_assert(LOC_CONTINUATION->array->count == 0);

  BEGIN_CODE
  INITIALIZE_FRAME_LOCALS(nframelocal);
  po->stack_depth += 4*nframelocal;
  END_CODE

  array = LOC_CONTINUATION->array = array_new(nframelocal);
  while (j--)
    array->items[j] = vinfo_new(RunTime_NewStack(
                         po->stack_depth - sizeof(long)*j, false, false));
}

#define INITIAL_STACK_DEPTH_INUSE  (INITIAL_STACK_DEPTH +                     \
                                     (!NEED_STACK_FRAME_HACK) * sizeof(long))

DEFINEFN
code_t* psyco_finish_return(PsycoObject* po, Source retval)
{
  code_t* code = po->code;
  int retpos;
  int nframelocal = LOC_CONTINUATION->array->count;

  /* 'retpos' is the position in the stack of the return address. */
  retpos = getstack(LOC_CONTINUATION->source);
  extra_assert(retpos != RunTime_StackNone);

  /* write the epilogue */
  WRITE_FRAME_EPILOGUE(retval, nframelocal);

  /* now clean up the stack up to retpos */
  STACK_CORRECTION(retpos - po->stack_depth);

  /* emit the 'RET' instruction */
  retpos -= INITIAL_STACK_DEPTH_INUSE;
  FUNCTION_RET(retpos);
  
  PsycoObject_Delete(po);
  return code;
}


/***************************************************************/
 /*** Condition Codes (a.k.a. the processor 'flags' register) ***/

#if HAVE_CCREG
static source_virtual_t cc_functions_table[CC_TOTAL];

DEFINEFN
condition_code_t cc_from_vsource(Source source)
{
	source_virtual_t* sv = VirtualTime_Get(source);
	return (condition_code_t) (sv - cc_functions_table);
}

static bool generic_computed_cc(PsycoObject* po, vinfo_t* v)
{
	/* also upon forking, because the condition codes cannot be
	   sent as arguments (function calls typically require adds
	   and subs to adjust the stack). */
	/* 'v' should be one of the po->ccregs[_] here */
	BEGIN_CODE
	code = psyco_compute_cc(po, code
#if REG_TOTAL > 0
                                , REG_NONE
#endif
                                );
	END_CODE
	return true;
}


DEFINEFN
vinfo_t* psyco_vinfo_condition(PsycoObject* po, condition_code_t cc)
{
  vinfo_t* result;
  if ((int)cc < CC_TOTAL)
    {
      int index = INDEX_CC(cc);
      if (po->ccregs[index] != NULL)
        {
          /* there is already a value in the processor flags register */
          condition_code_t prevcc = psyco_vsource_cc(po->ccregs[index]->source);
          extra_assert(prevcc != CC_ALWAYS_FALSE);
          
          if (prevcc == cc)
            {
              /* it is the same condition, so reuse it */
              result = po->ccregs[index];
              vinfo_incref(result);
              return result;
            }
          else
            {
              /* it is not the same condition at all, save the old one and
                 make a new one (should never occur with the ivm backend) */
              BEGIN_CODE
              NEED_CC();
              END_CODE
            }
        }
      extra_assert(po->ccregs[index] == NULL);
      result = vinfo_new(VirtualTime_New(cc_functions_table+(int)cc));
      po->ccregs[index] = result;
    }
  else
    result = vinfo_new(CompileTime_New(cc == CC_ALWAYS_TRUE));
  return result;
}

DEFINEFN
VirtualTimeSource psyco_source_condition(condition_code_t cc)
{
  return VirtualTime_New(cc_functions_table+(int)cc);
}

DEFINEFN
condition_code_t psyco_vsource_cc(Source source)
{
  if (is_virtualtime(source))
    {
      source_virtual_t* sv = VirtualTime_Get(source);
      if (cc_functions_table <= sv  &&  sv < cc_functions_table+CC_TOTAL)
        {
          /* 'sv' points within the cc_functions_table */
          return (condition_code_t) (sv - cc_functions_table);
        }
    }
  return CC_ALWAYS_FALSE;
}

DEFINEFN
void psyco_resolved_cc(PsycoObject* po, condition_code_t cc_known_true)
{
  if ((int)cc_known_true < CC_TOTAL)
    {
      vinfo_t* v;
      int index;

      index = INDEX_CC(cc_known_true);
      v = po->ccregs[index];
      if (v != NULL && psyco_vsource_cc(v->source) == cc_known_true)
        {
          sk_incref(&psyco_skOne);
          v->source = CompileTime_NewSk(&psyco_skOne);
          po->ccregs[index] = NULL;
        }

      index = INDEX_CC(INVERT_CC(cc_known_true));
      v = po->ccregs[index];
      if (v != NULL && psyco_vsource_cc(v->source) == INVERT_CC(cc_known_true))
        {
          sk_incref(&psyco_skZero);
          v->source = CompileTime_NewSk(&psyco_skZero);
          po->ccregs[index] = NULL;
        }
    }
}

#else /* if !HAVE_CCREG */

# error "this was meant for ivm, but now ivm also defines HAVE_CCREG."

#endif /* HAVE_CCREG */


/*****************************************************************/
 /***   run-time switches                                       ***/

static bool computed_promotion(PsycoObject* po, vinfo_t* v)
{
  /* uncomputable, but still use the address of computed_promotion() as a
     tag to figure out if a virtual source is a c_promotion_s structure. */
  return psyco_vsource_not_important.compute_fn(po, v);
}

DEFINEVAR c_promotion_t psyco_nonfixed_promotion;
DEFINEVAR c_promotion_t psyco_nonfixed_pyobj_promotion;
/*DEFINEVAR c_promotion_t psyco_nonfixed_promotion_mega;*/
DEFINEVAR c_promotion_t psyco_nonfixed_pyobj_promotion_mega;

DEFINEFN
bool psyco_vsource_is_promotion(VirtualTimeSource source)
{
  return VirtualTime_Get(source)->compute_fn == &computed_promotion;
}


/*****************************************************************/
 /***   Calling C functions                                     ***/

#define MAX_ARGUMENTS_COUNT    16

DEFINEFN
vinfo_t* psyco_generic_call(PsycoObject* po, void* c_function,
                            int flags, const char* arguments, ...)
{
	char argtags[MAX_ARGUMENTS_COUNT];
	long raw_args[MAX_ARGUMENTS_COUNT], args[MAX_ARGUMENTS_COUNT];
	int count, i, j, stackbase, totalstackspace = 0;
	vinfo_t* vresult;
	bool has_refs = false;

	va_list vargs;

#ifdef HAVE_STDARG_PROTOTYPES
	va_start(vargs, arguments);
#else
	va_start(vargs);
#endif
	extra_assert(c_function != NULL);

	for (count=0; arguments[count]; count++) {
		long arg;
		char tag;
		vinfo_t* vi;
		
		extra_assert(count <= MAX_ARGUMENTS_COUNT);
		raw_args[count] = arg = va_arg(vargs, long);
		tag = arguments[count];

		switch (tag) {
			
		case 'l':
			break;
			
		case 'v':
			/* Compute all values first */
			vi = (vinfo_t*) arg;
			if (!compute_vinfo(vi, po)) return NULL;
			if (!is_compiletime(vi->source)) {
				flags &= ~CfPure;
			}
			else {
				/* compile-time: get the value */
				arg = CompileTime_Get(vi->source)->value;
				tag = 'l';
			}
			break;

		case 'r':
			/* Push by-reference values in the stack now */
			vi = (vinfo_t*) arg;
			extra_assert(is_runtime(vi->source));
#if REG_TOTAL > 0
			if (getstack(vi->source) == RunTime_StackNone) {
				reg_t rg = getreg(vi->source);
				if (rg == REG_NONE) {
					/* for undefined sources, pushing
					   just any register will be fine */
					rg = REG_ANY_CALLER_SAVED;
				}
				BEGIN_CODE
				SAVE_REG_VINFO(vi, rg);
				END_CODE
			}
#endif
                        arg = RunTime_NewStack(getstack(vi->source),
                                               false, false);
			has_refs = true;
			break;

		case 'a':
		case 'A':
			has_refs = true;
			totalstackspace += sizeof(long) *
				((vinfo_array_t*) arg)->count;
			break;

		default:
			Py_FatalError("unknown character argument in"
				      " psyco_generic_call()");
		}
		args[count] = arg;
		argtags[count] = tag;
	}
	va_end(vargs);

        if (flags & CfPure) {
                /* calling a pure function with no run-time argument */
                long result;

                if (has_refs) {
                    for (i = 0; i < count; i++) {
                        if (argtags[i] == 'a' || argtags[i] == 'A') {
				int cnt = ((vinfo_array_t*)args[i])->count;
				args[i] = (long)malloc(cnt*sizeof(long));
                        }
#if ALL_CHECKS
                        if (argtags[i] == 'r')
				Py_FatalError("psyco_generic_call(): arg mode "
					      "incompatible with CfPure");
#endif
                    }
                }
				#ifdef __APPLE__
				/* Adjust # of arguments for MacOS 16-byte stack alignment */
                result = psyco_call_var(c_function, (count+3)&~3, args);
				#else
                result = psyco_call_var(c_function, count, args);
				#endif
                if (PyErr_Occurred()) {
                    if (has_refs)
                        for (i = 0; i < count; i++) 
                            if (argtags[i] == 'a' || argtags[i] == 'A')
                                free((void*)args[i]);
                    psyco_virtualize_exception(po);
                    return NULL;
                }
                if (has_refs) {
                    for (i = 0; i < count; i++)
                        if (argtags[i] == 'a' || argtags[i] == 'A') {
                            vinfo_array_t* array = (vinfo_array_t*)raw_args[i];
                            long sk_flag = (argtags[i] == 'a') ? 0 : SkFlagPyObj;
                            for (j = 0; j < array->count; j++) {
                                array->items[j] = vinfo_new(CompileTime_NewSk(
                                    sk_new( ((long*)args[i])[j], sk_flag)));
                            }
                            free((void*)args[i]);
                        }
                }

		if (flags & CfPyErrMask) {
			/* such functions are rarely pure, but there are
			   exceptions with CfPyErrNotImplemented */
			vresult = generic_call_ct(flags, result);
			if (vresult != NULL)
				return vresult;
		}
		
		switch (flags & CfReturnMask) {

		case CfReturnNormal:
			vresult = vinfo_new(CompileTime_New(result));
			break;
			
		case CfReturnRef:
			vresult = vinfo_new(CompileTime_NewSk(sk_new(result,
								SkFlagPyObj)));
			break;

		default:
			vresult = (vinfo_t*) 1;   /* anything non-NULL */
		}
		return vresult;
	}

#ifdef CALL_SET_ARG_FROM_ADDR_CLOBBER_REG
	if (has_refs) {
		/* we will need a trash register to compute the references
		   we push later. The following three lines prevent another
		   argument which would currently be in the same trash
		   register from being pushed from the register after we
		   clobbered it. */
		BEGIN_CODE
		NEED_REGISTER(CALL_SET_ARG_FROM_ADDR_CLOBBER_REG);
		END_CODE
	}
#endif

	BEGIN_CODE
	NEED_CC();

	for (count=0; arguments[count]; count++) {
		if (argtags[count] == 'v') {
			/* We collect all the sources in 'args' now,
			   before SAVE_REGS_FN_CALLS which might move
			   some run-time values into the stack. In this
			   case the old copy in the registers is still
			   useable to PUSH it for the C function call. */
			RunTimeSource src = ((vinfo_t*)(args[count]))->source;
			args[count] = (long) src;
		}
	}

	SAVE_REGS_FN_CALLS(false);   /* CC saved above */
	stackbase = po->stack_depth;
	po->stack_depth += totalstackspace;
	STACK_CORRECTION(totalstackspace);
	CALL_STACK_ALIGN(count);
	for (i=count; i--; ) {
		switch (argtags[i]) {
			
		case 'v':
			CALL_SET_ARG_FROM_RT   (args[i], i, count);
			break;
			
		case 'r':
			CALL_SET_ARG_FROM_ADDR (args[i], i, count);
			break;
			
		case 'a':
		case 'A':
		{
			vinfo_array_t* array = (vinfo_array_t*) args[i];
			bool with_reference = (argtags[i] == 'A');
			int j = array->count;
			while (j > 0) {
				stackbase += sizeof(long);
				array->items[--j] = vinfo_new(
						RunTime_NewStack(stackbase,
							with_reference, false));
			}
			CALL_SET_ARG_FROM_ADDR(array->items[0]->source, i,count);
			break;
		}
		
		default:
			CALL_SET_ARG_IMMED   (args[i], i, count);
			break;
		}
	}
	CALL_C_FUNCTION                      (c_function, count);
	END_CODE

	switch (flags & CfReturnMask) {

	case CfReturnNormal:
		vresult = bfunction_result(po, false);
		break;

	case CfReturnRef:
		vresult = bfunction_result(po, true);
		break;

	default:
		if ((flags & CfPyErrMask) == 0)
			return (vinfo_t*) 1;   /* anything non-NULL */
		
		vresult = bfunction_result(po, false);
		vresult = generic_call_check(po, flags, vresult);
		if (vresult == NULL)
			goto error_detected;
		vinfo_decref(vresult, po);
		return (vinfo_t*) 1;   /* anything non-NULL */
	}
	
        if (flags & CfPyErrMask) {
		vresult = generic_call_check(po, flags, vresult);
		if (vresult == NULL)
			goto error_detected;
	}
	return vresult;

   error_detected:
	/* if the called function returns an error, we then assume that
	   it did not actually fill the arrays */
	if (has_refs) {
		for (i = 0; i < count; i++)
			if (argtags[i] == 'a' || argtags[i] == 'A') {
				vinfo_array_t* array = (vinfo_array_t*)args[i];
				int j = array->count;
				while (j--) {
					vinfo_t* v = array->items[j];
					array->items[j] = NULL;
					v->source = remove_rtref(v->source);
					vinfo_decref(v, po);
				}
                        }
	}

	return NULL;
}


DEFINEFN
void psyco_inline_enter(PsycoObject* po)
{
	struct stack_frame_info_s* finfo = psyco_finfo(NULL, po);
	BEGIN_CODE
	ABOUT_TO_CALL_SUBFUNCTION((long) finfo);
	END_CODE
}

DEFINEFN
void psyco_inline_exit (PsycoObject* po)
{
	BEGIN_CODE
	RETURNED_FROM_SUBFUNCTION();
	END_CODE
}


/*****************************************************************/
 /***   Emit common instructions                                ***/

/* forward */
static condition_code_t int_cmp_i(PsycoObject* po, vinfo_t* rt1,
                                  long immed2, int py_op);

DEFINEFN
condition_code_t integer_non_null(PsycoObject* po, vinfo_t* vi)
{
	condition_code_t result;
	
	if (is_virtualtime(vi->source)) {
		result = psyco_vsource_cc(vi->source);
		if (result != CC_ALWAYS_FALSE)
			return result;
		if (!compute_vinfo(vi, po))
			return CC_ERROR;
	}
	if (is_compiletime(vi->source)) {
		if (CompileTime_Get(vi->source)->value != 0)
			return CC_ALWAYS_TRUE;
		else
			return CC_ALWAYS_FALSE;
	}
	BEGIN_CODE
	CHECK_NONZERO_FROM_RT(vi->source, result);
	END_CODE
	return result;
}

DEFINEFN
condition_code_t integer_NON_NULL(PsycoObject* po, vinfo_t* vi)
{
	condition_code_t result;

	if (vi == NULL)
		return CC_ERROR;

        result = integer_non_null(po, vi);

	/* 'vi' cannot be a reference to a Python object if we are
	   asking ourselves if it is NULL or not. So the following
	   vinfo_decref() will not emit a Py_DECREF() that would
	   clobber the condition code. We check all this. */
#if ALL_CHECKS
	extra_assert(!has_rtref(vi->source));
	{ code_t* code1 = po->code;
#endif
	vinfo_decref(vi, po);
#if ALL_CHECKS
	extra_assert(po->code == code1); }
#endif
	return result;
}

#define GENERIC_BINARY_HEADER                   \
  if (!compute_vinfo(v2, po) || !compute_vinfo(v1, po)) return NULL

#define GENERIC_BINARY_HEADER_i                 \
  if (!compute_vinfo(v1, po)) return NULL

#define GENERIC_BINARY_CT_CT(c_code)                            \
  if (is_compiletime(v1->source) && is_compiletime(v2->source)) \
    {                                                           \
      long a = CompileTime_Get(v1->source)->value;              \
      long b = CompileTime_Get(v2->source)->value;              \
      long c = (c_code);                                        \
      return vinfo_new(CompileTime_New(c));                     \
    }

DEFINEFN
vinfo_t* integer_add(PsycoObject* po, vinfo_t* v1, vinfo_t* v2, bool ovf)
{
  GENERIC_BINARY_HEADER;
  if (is_compiletime(v1->source))
    {
      long a = CompileTime_Get(v1->source)->value;
      if (a == 0)
        {
          /* adding zero to v2 */
          vinfo_incref(v2);
          return v2;
        }
      if (is_compiletime(v2->source))
        {
          long b = CompileTime_Get(v2->source)->value;
          long c = a + b;
          if (ovf && (c^a) < 0 && (c^b) < 0)
            return NULL;   /* overflow */
          return vinfo_new(CompileTime_New(c));
        }
      if (!ovf)
        return bint_add_i(po, v2, a, false);
    }
  else
    if (is_compiletime(v2->source))
      {
        long b = CompileTime_Get(v2->source)->value;
        if (b == 0)
          {
            /* adding zero to v1 */
            vinfo_incref(v1);
            return v1;
          }
        if (!ovf)
          return bint_add_i(po, v1, b, false);
      }
  return BINARY_INSTR_ADD(ovf, ovf && is_nonneg(v1->source)
                                   && is_nonneg(v2->source));
}

DEFINEFN
vinfo_t* integer_add_i(PsycoObject* po, vinfo_t* v1, long value2, bool unsafe)
{
  if (value2 == 0)
    {
      /* adding zero to v1 */
      vinfo_incref(v1);
      return v1;
    }
  else
    {
      GENERIC_BINARY_HEADER_i;
      if (is_compiletime(v1->source))
        {
          long c = CompileTime_Get(v1->source)->value + value2;
          return vinfo_new(CompileTime_New(c));
        }
      return bint_add_i(po, v1, value2, unsafe);
    }
}

DEFINEFN
vinfo_t* integer_sub(PsycoObject* po, vinfo_t* v1, vinfo_t* v2, bool ovf)
{
  GENERIC_BINARY_HEADER;
  if (is_compiletime(v1->source))
    {
      long a = CompileTime_Get(v1->source)->value;
      if (is_compiletime(v2->source))
        {
          long b = CompileTime_Get(v2->source)->value;
          long c = a - b;
          if (ovf && (c^a) < 0 && (c^~b) < 0)
            return NULL;   /* overflow */
          return vinfo_new(CompileTime_New(c));
        }
    }
  else
    if (is_compiletime(v2->source))
      {
        long b = CompileTime_Get(v2->source)->value;
        if (b == 0)
          {
            /* subtracting zero from v1 */
            vinfo_incref(v1);
            return v1;
          }
        if (!ovf)
          return bint_add_i(po, v1, -b, false);
      }
  return BINARY_INSTR_SUB(ovf, false);
}

DEFINEFN
vinfo_t* integer_or(PsycoObject* po, vinfo_t* v1, vinfo_t* v2)
{
  GENERIC_BINARY_HEADER;
  GENERIC_BINARY_CT_CT(a | b);
  return BINARY_INSTR_OR(false, is_nonneg(v1->source) &&
			        is_nonneg(v2->source));
}

DEFINEFN
vinfo_t* integer_xor(PsycoObject* po, vinfo_t* v1, vinfo_t* v2)
{
  GENERIC_BINARY_HEADER;
  GENERIC_BINARY_CT_CT(a ^ b);
  return BINARY_INSTR_XOR(false, is_nonneg(v1->source) &&
			         is_nonneg(v2->source));
}

DEFINEFN
vinfo_t* integer_and(PsycoObject* po, vinfo_t* v1, vinfo_t* v2)
{
  GENERIC_BINARY_HEADER;
  GENERIC_BINARY_CT_CT(a & b);
  return BINARY_INSTR_AND(false, is_nonneg(v1->source) ||
			         is_nonneg(v2->source));
}

static vinfo_t* int_mul_i(PsycoObject* po, vinfo_t* v1, long value2,
                                   bool ovf)
{
  switch (value2) {
  case 0:
    return vinfo_new(CompileTime_New(0));
  case 1:
    vinfo_incref(v1);
    return v1;
  }
  if (((value2-1) & value2) == 0 && value2 >= 0 && !ovf)
    {
      /* value2 is a power of two */
      return bint_lshift_i(po, v1, intlog2(value2));
    }
  else
    {
      return bint_mul_i(po, v1, value2, ovf);
    }
}

DEFINEFN
vinfo_t* integer_mul(PsycoObject* po, vinfo_t* v1, vinfo_t* v2, bool ovf)
{
  GENERIC_BINARY_HEADER;
  if (is_compiletime(v1->source))
    {
      long a = CompileTime_Get(v1->source)->value;
      if (is_compiletime(v2->source))
        {
          long b = CompileTime_Get(v2->source)->value;
          /* unlike Python, we use a function written in assembly
             to perform the product overflow checking */
          if (ovf && psyco_int_mul_ovf(a, b))
            return NULL;   /* overflow */
          return vinfo_new(CompileTime_New(a * b));
        }
      return int_mul_i(po, v2, a, ovf);
    }
  else
    if (is_compiletime(v2->source))
      {
        long b = CompileTime_Get(v2->source)->value;
        return int_mul_i(po, v1, b, ovf);
      }
  return BINARY_INSTR_MUL(ovf, ovf && is_rtnonneg(v1->source)
                                   && is_rtnonneg(v2->source));
}

DEFINEFN
vinfo_t* integer_mul_i(PsycoObject* po, vinfo_t* v1, long value2)
{
  GENERIC_BINARY_HEADER_i;
  if (is_compiletime(v1->source))
    {
      long c = CompileTime_Get(v1->source)->value * value2;
      return vinfo_new(CompileTime_New(c));
    }
  return int_mul_i(po, v1, value2, false);
}

DEFINEFN
vinfo_t* integer_lshift(PsycoObject* po, vinfo_t* v1, vinfo_t* v2)
{
  condition_code_t cc;
  GENERIC_BINARY_HEADER;
  if (is_compiletime(v2->source))
    return integer_lshift_i(po, v1, CompileTime_Get(v2->source)->value);

  cc = int_cmp_i(po, v2, LONG_BIT, Py_GE|COMPARE_UNSIGNED);
  if (cc == CC_ERROR)
    return NULL;

  if (runtime_condition_f(po, cc))
    {
      cc = int_cmp_i(po, v2, 0, Py_LT);
      if (cc == CC_ERROR)
        return NULL;
      if (runtime_condition_f(po, cc))
        {
          PycException_SetString(po, PyExc_ValueError, "negative shift count");
          return NULL;
        }
      return vinfo_new(CompileTime_New(0));
    }
  return BINARY_INSTR_LSHIFT(false);
}

DEFINEFN
vinfo_t* integer_lshift_i(PsycoObject* po, vinfo_t* v1, long counter)
{
  GENERIC_BINARY_HEADER_i;
  if (0 < counter && counter < LONG_BIT)
    {
      if (is_compiletime(v1->source))
        {
          long c = CompileTime_Get(v1->source)->value << counter;
          return vinfo_new(CompileTime_New(c));
        }
      else
        return bint_lshift_i(po, v1, counter);
    }
  else if (counter == 0)
    {
      vinfo_incref(v1);
      return v1;
    }
  else if (counter >= LONG_BIT)
    return vinfo_new(CompileTime_New(0));
  else
    {
      PycException_SetString(po, PyExc_ValueError, "negative shift count");
      return NULL;
    }
}

DEFINEFN      /* signed */
vinfo_t* integer_rshift(PsycoObject* po, vinfo_t* v1, vinfo_t* v2)
{
  condition_code_t cc;
  GENERIC_BINARY_HEADER;
  if (is_compiletime(v2->source))
    return integer_rshift_i(po, v1, CompileTime_Get(v2->source)->value);

  cc = int_cmp_i(po, v2, LONG_BIT, Py_GE|COMPARE_UNSIGNED);
  if (cc == CC_ERROR)
    return NULL;

  if (runtime_condition_f(po, cc))
    {
      cc = int_cmp_i(po, v2, 0, Py_LT);
      if (cc == CC_ERROR)
        return NULL;
      if (runtime_condition_f(po, cc))
        {
          PycException_SetString(po, PyExc_ValueError, "negative shift count");
          return NULL;
        }
      return integer_rshift_i(po, v1, LONG_BIT-1);
    }
  return BINARY_INSTR_RSHIFT(is_nonneg(v1->source));
}

DEFINEFN      /* signed */
vinfo_t* integer_rshift_i(PsycoObject* po, vinfo_t* v1, long counter)
{
  GENERIC_BINARY_HEADER_i;
  if (counter >= LONG_BIT-1)
    {
      if (is_nonneg(v1->source))
        return vinfo_new(CompileTime_New(0));
      counter = LONG_BIT-1;
    }
  if (counter > 0)
    {
      if (is_compiletime(v1->source))
        {
          long c = ((long)(CompileTime_Get(v1->source)->value)) >> counter;
          return vinfo_new(CompileTime_New(c));
        }
      else
        return bint_rshift_i(po, v1, counter);
    }
  else if (counter == 0)
    {
      vinfo_incref(v1);
      return v1;
    }
  else
    {
      PycException_SetString(po, PyExc_ValueError, "negative shift count");
      return NULL;
    }
}

DEFINEFN
vinfo_t* integer_urshift_i(PsycoObject* po, vinfo_t* v1, long counter)
{
  GENERIC_BINARY_HEADER_i;
  if (0 < counter && counter < LONG_BIT)
    {
      if (is_compiletime(v1->source))
        {
          long c = ((unsigned long)(CompileTime_Get(v1->source)->value)) >> counter;
          return vinfo_new(CompileTime_New(c));
        }
      else
        return bint_urshift_i(po, v1, counter);
    }
  else if (counter == 0)
    {
      vinfo_incref(v1);
      return v1;
    }
  else if (counter >= LONG_BIT)
    return vinfo_new(CompileTime_New(0));
  else
    {
      PycException_SetString(po, PyExc_ValueError, "negative shift count");
      return NULL;
    }
}

/* DEFINEFN */
/* vinfo_t* integer_lshift(PsycoObject* po, vinfo_t* v1, vinfo_t* v2) */
/* { */
/*   NonVirtualSource v1s, v2s; */
/*   v2s = vinfo_compute(v2, po); */
/*   if (v2s == SOURCE_ERROR) return NULL; */
/*   if (is_compiletime(v2s)) */
/*     return integer_lshift_i(po, v1, CompileTime_Get(v2s)->value); */
  
/*   v1s = vinfo_compute(v1, po); */
/*   if (v1s == SOURCE_ERROR) return NULL; */
/*   XXX implement me */
/* } */

#define GENERIC_UNARY_HEADER                            \
  if (!compute_vinfo(v1, po)) return NULL;

#define GENERIC_UNARY_CT(c_code, ovf, c_ovf)            \
  if (is_compiletime(v1->source))                       \
    {                                                   \
      long a = CompileTime_Get(v1->source)->value;      \
      long c = (c_code);                                \
      if ((ovf) && (c_ovf))                             \
        return NULL;                                    \
      return vinfo_new(CompileTime_New(c));             \
    }

DEFINEFN
vinfo_t* integer_inv(PsycoObject* po, vinfo_t* v1)
{
  GENERIC_UNARY_HEADER;
  GENERIC_UNARY_CT(~a, false, false);
  return UNARY_INSTR_INV(false, false);
}

DEFINEFN
vinfo_t* integer_neg(PsycoObject* po, vinfo_t* v1, bool ovf)
{
  GENERIC_UNARY_HEADER;
  GENERIC_UNARY_CT(-a, ovf, c == (-LONG_MAX-1));
  return UNARY_INSTR_NEG(ovf, false);
}

DEFINEFN
vinfo_t* integer_abs(PsycoObject* po, vinfo_t* v1, bool ovf)
{
  GENERIC_UNARY_HEADER;
  if (is_nonneg(v1->source))
    {
      vinfo_incref(v1);
      return v1;
    }
  GENERIC_UNARY_CT(a<0 ? -a : a, ovf, c == (-LONG_MAX-1));
  return UNARY_INSTR_ABS(ovf, true);  /* nb. result assumed to be positive,
                                         which is false in case of overflow */
}

static condition_code_t immediate_compare(long a, long b, int base_py_op)
{
  switch (base_py_op) {
    case Py_LT:  return a < b  ? CC_ALWAYS_TRUE : CC_ALWAYS_FALSE;
    case Py_LE:  return a <= b ? CC_ALWAYS_TRUE : CC_ALWAYS_FALSE;
    case Py_EQ|COMPARE_UNSIGNED:
    case Py_EQ:  return a == b ? CC_ALWAYS_TRUE : CC_ALWAYS_FALSE;
    case Py_NE|COMPARE_UNSIGNED:
    case Py_NE:  return a != b ? CC_ALWAYS_TRUE : CC_ALWAYS_FALSE;
    case Py_GT:  return a > b  ? CC_ALWAYS_TRUE : CC_ALWAYS_FALSE;
    case Py_GE:  return a >= b ? CC_ALWAYS_TRUE : CC_ALWAYS_FALSE;

  case Py_LT|COMPARE_UNSIGNED:  return ((unsigned long) a) <  ((unsigned long) b)
                                  ? CC_ALWAYS_TRUE : CC_ALWAYS_FALSE;
  case Py_LE|COMPARE_UNSIGNED:  return ((unsigned long) a) <= ((unsigned long) b)
                                  ? CC_ALWAYS_TRUE : CC_ALWAYS_FALSE;
  case Py_GT|COMPARE_UNSIGNED:  return ((unsigned long) a) >  ((unsigned long) b)
                                  ? CC_ALWAYS_TRUE : CC_ALWAYS_FALSE;
  case Py_GE|COMPARE_UNSIGNED:  return ((unsigned long) a) >= ((unsigned long) b)
                                  ? CC_ALWAYS_TRUE : CC_ALWAYS_FALSE;
  default:
    Py_FatalError("immediate_compare(): bad py_op");
    return CC_ERROR;
  }
}

static condition_code_t int_cmp_i(PsycoObject* po, vinfo_t* rt1,
                                  long immed2, int py_op)
{
  int base_py_op = py_op & COMPARE_OP_MASK;
  extra_assert(is_runtime(rt1->source));
  /* detect easy cases */
  if (immed2 == 0)
    {
      if (is_rtnonneg(rt1->source))   /* if we know that rt1>=0 */
        switch (base_py_op) {
        case Py_LT:   /* rt1 < 0 */
          return CC_ALWAYS_FALSE;
        case Py_GE:  /* rt1 >= 0 */
          return CC_ALWAYS_TRUE;
        default:
          ; /* pass */
        }
      switch (base_py_op) {
      case Py_LT|COMPARE_UNSIGNED:   /* (unsigned) rt1 < 0 */
        return CC_ALWAYS_FALSE;
      case Py_GE|COMPARE_UNSIGNED:  /* (unsigned) rt1 >= 0 */
        return CC_ALWAYS_TRUE;
      default:
        ; /* pass */
      }
    }
  else if (immed2 < 0)
    {
      if (is_rtnonneg(rt1->source))  /* rt1>=0 && immed2<0 */
        {
          switch (base_py_op) {
          case Py_EQ:    /* rt1 == immed2 */
          case Py_LT:    /* rt1 <  immed2 */
          case Py_LE:   /* rt1 <= immed2 */
          case Py_GT|COMPARE_UNSIGNED:   /* (unsigned) rt1 >  immed2 */
          case Py_GE|COMPARE_UNSIGNED:  /* (unsigned) rt1 >= immed2 */
            return CC_ALWAYS_FALSE;
          case Py_NE:   /* rt1 != immed2 */
          case Py_GE:   /* rt1 >= immed2 */
          case Py_GT:    /* rt1 >  immed2 */
          case Py_LE|COMPARE_UNSIGNED:  /* (unsigned) rt1 <= immed2 */
          case Py_LT|COMPARE_UNSIGNED:   /* (unsigned) rt1 <  immed2 */
            return CC_ALWAYS_TRUE;
          default:
            ; /* pass */
          }
        }
      if (immed2 == LONG_MIN)
        {
          switch (base_py_op) {
          case Py_LT:    /* rt1 <  LONG_MIN */
            return CC_ALWAYS_FALSE;
          case Py_GE:   /* rt1 >= LONG_MIN */
            return CC_ALWAYS_TRUE;
          case Py_EQ:    /* rt1 == LONG_MIN */
          case Py_LE:   /* rt1 <= LONG_MIN */
            if (py_op & CHEAT_MAXINT) return CC_ALWAYS_FALSE;
            break;
          case Py_NE:   /* rt1 != LONG_MIN */
          case Py_GT:    /* rt1 >  LONG_MIN */
            if (py_op & CHEAT_MAXINT) return CC_ALWAYS_TRUE;
            break;
          default:
            ; /* pass */
          }
        }
    }
  else if (immed2 == LONG_MAX)
    {
      if (is_rtnonneg(rt1->source))   /* if we know that rt1>=0 */
        {
          switch (base_py_op) {
          case Py_GT|COMPARE_UNSIGNED:   /* (unsigned) rt1 >  LONG_MAX */
            return CC_ALWAYS_FALSE;
          case Py_LE|COMPARE_UNSIGNED:  /* (unsigned) rt1 <= LONG_MAX */
            return CC_ALWAYS_TRUE;
          case Py_GE|COMPARE_UNSIGNED:  /* (unsigned) rt1 >= LONG_MAX */
            if (py_op & CHEAT_MAXINT) return CC_ALWAYS_FALSE;
            break;
          case Py_LT|COMPARE_UNSIGNED:   /* (unsigned) rt1 <  LONG_MAX */
            if (py_op & CHEAT_MAXINT) return CC_ALWAYS_TRUE;
            break;
          default:
            ; /* pass */
          }
        }
      switch (base_py_op) {
      case Py_LE:   /* rt1 <= LONG_MAX */
        return CC_ALWAYS_TRUE;
      case Py_GT:    /* rt1 >  LONG_MAX */
        return CC_ALWAYS_FALSE;
      case Py_EQ:    /* rt1 == LONG_MAX */
      case Py_GE:   /* rt1 >= LONG_MAX */
        if (py_op & CHEAT_MAXINT) return CC_ALWAYS_FALSE;
        break;
      case Py_NE:   /* rt1 != LONG_MAX */
      case Py_LT:    /* rt1 <  LONG_MAX */
        if (py_op & CHEAT_MAXINT) return CC_ALWAYS_TRUE;
        break;
      default:
        ; /* pass */
      }
    }
  /* end of easy cases */
  return bint_cmp_i(po, base_py_op, rt1, immed2);
}

static const int inverted_py_op[8] = {
          /* Py_LT: */  Py_GT,
          /* Py_LE: */  Py_GE,
          /* Py_EQ: */  Py_EQ,
          /* Py_NE: */  Py_NE,
          /* Py_GT: */  Py_LT,
          /* Py_GE: */  Py_LE,
	  /* (6)    */  -1,
	  /* (7)    */  -1 };

DEFINEFN
condition_code_t integer_cmp(PsycoObject* po, vinfo_t* v1,
                             vinfo_t* v2, int py_op)
{
  int base_py_op = py_op & COMPARE_OP_MASK;
  
  if (vinfo_known_equal(v1, v2))
    goto same_source;

  if (!compute_vinfo(v1, po) || !compute_vinfo(v2, po))
    return CC_ERROR;

  if (vinfo_known_equal(v1, v2))
    {
    same_source:
      /* comparing equal sources */
      switch (base_py_op) {
      case Py_LE:
      case Py_EQ:
      case Py_GE:
        return CC_ALWAYS_TRUE;
      default:
        return CC_ALWAYS_FALSE;
      }
    }
  if (is_compiletime(v1->source))
    if (is_compiletime(v2->source))
      {
        long a = CompileTime_Get(v1->source)->value;
        long b = CompileTime_Get(v2->source)->value;
        return immediate_compare(a, b, base_py_op);
      }
    else
      {
        /* invert the two operands because (assumedly) the processor has
           only CMP xxx,immed and not CMP immed,xxx */
        py_op = inverted_py_op[py_op & COMPARE_BASE_MASK] |
		(py_op & ~COMPARE_BASE_MASK);
        return int_cmp_i(po, v2, CompileTime_Get(v1->source)->value, py_op);
      }
  else
    if (is_compiletime(v2->source))
      {
        return int_cmp_i(po, v1, CompileTime_Get(v2->source)->value, py_op);
      }
    else
      {
        return BINARY_INSTR_CMP(base_py_op);
      }
}

DEFINEFN
condition_code_t integer_cmp_i(PsycoObject* po, vinfo_t* v1,
                               long value2, int py_op)
{
  if (!compute_vinfo(v1, po)) return CC_ERROR;
  
  if (is_compiletime(v1->source))
    {
      long a = CompileTime_Get(v1->source)->value;
      return immediate_compare(a, value2, py_op);
    }
  else
    return int_cmp_i(po, v1, value2, py_op);
}

DEFINEFN
vinfo_t* integer_conditional(PsycoObject* po, condition_code_t cc,
                             long immed_true, long immed_false)
{
  switch ((int)cc) {
  case (int)CC_ALWAYS_FALSE:
    return vinfo_new(CompileTime_New(immed_false));

  case (int)CC_ALWAYS_TRUE:
    return vinfo_new(CompileTime_New(immed_true));

  default:
    return BINARY_INSTR_COND(cc, immed_true, immed_false);
  }
}


INITIALIZATIONFN
void psyco_codegen_init(void)
{
#if HAVE_CCREG
  int i;
  for (i=0; i<CC_TOTAL; i++)
    {
      /* the condition codes cannot be passed across function calls */
      INIT_SVIRTUAL_NOCALL(cc_functions_table[i], generic_computed_cc, 0);
    }
#endif

  psyco_nonfixed_promotion.header.compute_fn = &computed_promotion;
  psyco_nonfixed_promotion.pflags = 0;

  psyco_nonfixed_pyobj_promotion.header.compute_fn = &computed_promotion;
  psyco_nonfixed_pyobj_promotion.pflags = PFlagPyObj;

/*psyco_nonfixed_promotion_mega.header.compute_fn = &computed_promotion;
  psyco_nonfixed_promotion_mega.pflags = PFlagMegamorphic;*/

  psyco_nonfixed_pyobj_promotion_mega.header.compute_fn = &computed_promotion;
  psyco_nonfixed_pyobj_promotion_mega.pflags = PFlagPyObj | PFlagMegamorphic;
}
