/* 
 * Psyco version of python math module, mathmodule.c 
 *
 * TODO: 
 * - raise python exceptions on math errors (domain error etc)
 * - implement:
 *   - frexp()
 *   - ldexp()
 *   - log()
 *   - log10()
 *   - modf()
 */

#include "../initialize.h"
#if HAVE_FP_FN_CALLS    /* disable float optimizations if functions with
                           float/double arguments are not implemented
                           in the back-end */

#ifndef _MSC_VER
#ifndef __STDC__
extern double fmod (double, double);
extern double frexp (double, int *);
extern double ldexp (double, int);
extern double modf (double, double *);
#endif /* __STDC__ */
#endif /* _MSC_VER */


#include <math.h>

#define CIMPL_MATH_FUNC1(funcname, func, libfunc) \
    static int cimpl_math_##func(double a, double* result) { \
        errno = 0; \
        PyFPE_START_PROTECT(funcname, return -1) \
        *result = libfunc(a); \
        PyFPE_END_PROTECT(*result); \
        return 0; \
    }

#define CIMPL_MATH_FUNC2(funcname, func, libfunc) \
    static int cimpl_math_##func(double a, double b, double* result) { \
        errno = 0; \
        PyFPE_START_PROTECT(funcname, return -1) \
        *result = libfunc(a,b); \
        PyFPE_END_PROTECT(*result); \
        return 0; \
    }

/* 
 * This is almost but not quite the same as the 
 * version in pfloatobject.c. The error handling 
 * on invalid args is different
 */
#define PMATH_CONVERT_TO_DOUBLE(vobj, v1, v2, ERRORACTION)	\
    switch (psyco_convert_to_double(po, vobj, &v1, &v2)) {	\
    case true:							\
        break;   /* fine */					\
    case false:							\
        ERRORACTION;  /* error or promotion */			\
    default:							\
        PycException_SetString(po, PyExc_TypeError,		\
            "bad argument type for built-in operation");	\
        ERRORACTION;						\
    }

#define PMATH_RELEASE_DOUBLE(v1, v2) \
    vinfo_decref(v2, po); \
    vinfo_decref(v1, po);

#define PMATH_FUNC1(funcname, func ) \
    static PyCFunction fallback_##func; \
    static vinfo_t* pmath_##func(PsycoObject* po, vinfo_t* vself, vinfo_t* varg) { \
        vinfo_t *a1, *a2, *x; \
        vinfo_array_t* result; \
        vinfo_t *v; \
        int tuplesize = PsycoTuple_Load(varg); \
        if (tuplesize != 1){ /* wrong or unknown number of arguments */ \
          return psyco_generic_call(po, fallback_##func, \
				    CfReturnRef|CfPyErrIfNull, \
				    "lv", NULL, varg); \
        } \
        v = PsycoTuple_GET_ITEM(varg, 0); \
        PMATH_CONVERT_TO_DOUBLE(v,a1,a2,return NULL);      \
        result = array_new(2); \
        x = psyco_generic_call(po, cimpl_math_##func, CfPure|CfNoReturnValue|CfPyErrIfNonNull, \
                                  "vva",a1,a2,result); \
        PMATH_RELEASE_DOUBLE(a1,a2); \
        if (x != NULL) \
            x = PsycoFloat_FROM_DOUBLE(result->items[0], result->items[1]); \
        array_release(result); \
        return x; \
    }


#define PMATH_FUNC2(funcname, func ) \
    static PyCFunction fallback_##func; \
    static vinfo_t* pmath_##func(PsycoObject* po, vinfo_t* vself, vinfo_t* varg) { \
        vinfo_t *a1, *a2, *b1, *b2, *x; \
        vinfo_array_t* result; \
        vinfo_t *v1, *v2; \
        int tuplesize = PsycoTuple_Load(varg); \
        if (tuplesize != 2){ /* wrong or unknown number of arguments */ \
          return psyco_generic_call(po, fallback_##func, \
				    CfReturnRef|CfPyErrIfNull, \
				    "lv", NULL, varg); \
        } \
        v1 = PsycoTuple_GET_ITEM(varg, 0); \
        v2 = PsycoTuple_GET_ITEM(varg, 1); \
        PMATH_CONVERT_TO_DOUBLE(v1,a1,a2,return NULL);     \
        PMATH_CONVERT_TO_DOUBLE(v2,b1,b2,goto cleanup);                \
        result = array_new(2); \
        x = psyco_generic_call(po, cimpl_math_##func, CfPure|CfNoReturnValue|CfPyErrIfNonNull, \
                               "vvvva",a1,a2,b1,b2,result); \
        PMATH_RELEASE_DOUBLE(a1,a2); \
        PMATH_RELEASE_DOUBLE(b1,b2); \
        if (x != NULL) \
            x = PsycoFloat_FROM_DOUBLE(result->items[0], result->items[1]); \
        array_release(result); \
        return x; \
    cleanup:\
        PMATH_RELEASE_DOUBLE(a1,a2); \
        return NULL; \
    }

/* the functions cimpl_math_sin() etc */
CIMPL_MATH_FUNC1("acos", acos, acos)
CIMPL_MATH_FUNC1("asin", asin, asin)
CIMPL_MATH_FUNC1("atan", atan, atan)
CIMPL_MATH_FUNC2("atan2", atan2, atan2)
CIMPL_MATH_FUNC1("ceil", ceil, ceil)
CIMPL_MATH_FUNC1("cos", cos, cos)
CIMPL_MATH_FUNC1("cosh", cosh, cosh)
CIMPL_MATH_FUNC1("exp", exp, exp)
CIMPL_MATH_FUNC1("fabs", fabs, fabs)
CIMPL_MATH_FUNC1("floor", floor, floor)
CIMPL_MATH_FUNC2("fmod", fmod, fmod)
CIMPL_MATH_FUNC2("hypot", hypot, hypot)
/*CIMPL_MATH_FUNC2("power", power, pow)*/
CIMPL_MATH_FUNC2("pow", pow, pow)
CIMPL_MATH_FUNC1("sin", sin, sin)
CIMPL_MATH_FUNC1("sinh", sinh, sinh)
CIMPL_MATH_FUNC1("sqrt", sqrt, sqrt)
CIMPL_MATH_FUNC1("tan", tan, tan)
CIMPL_MATH_FUNC1("tanh", tanh, tanh)

/* the functions pmath_sin() etc */
PMATH_FUNC1("acos", acos)
PMATH_FUNC1("asin", asin)
PMATH_FUNC1("atan", atan)
PMATH_FUNC2("atan2", atan2)
PMATH_FUNC1("ceil", ceil)
PMATH_FUNC1("cos", cos)
PMATH_FUNC1("cosh", cosh)
PMATH_FUNC1("exp", exp)
PMATH_FUNC1("fabs", fabs)
PMATH_FUNC1("floor", floor)
PMATH_FUNC2("fmod", fmod)
PMATH_FUNC2("hypot", hypot)
/*PMATH_FUNC2("power", power)*/
PMATH_FUNC2("pow", pow)
PMATH_FUNC1("sin", sin)
PMATH_FUNC1("sinh", sinh)
PMATH_FUNC1("sqrt", sqrt)
PMATH_FUNC1("tan", tan)
PMATH_FUNC1("tanh", tanh)
      
INITIALIZATIONFN
void psyco_initmath(void)
{
    PyObject* md = Psyco_DefineMetaModule("math");
    
    fallback_acos = Psyco_DefineModuleFn(md, "acos", METH_VARARGS, pmath_acos);
    fallback_asin = Psyco_DefineModuleFn(md, "asin", METH_VARARGS, pmath_asin);
    fallback_atan = Psyco_DefineModuleFn(md, "atan", METH_VARARGS, pmath_atan);
    fallback_atan2= Psyco_DefineModuleFn(md, "atan2",METH_VARARGS, pmath_atan2);
    fallback_ceil = Psyco_DefineModuleFn(md, "ceil", METH_VARARGS, pmath_ceil);
    fallback_cos  = Psyco_DefineModuleFn(md, "cos",  METH_VARARGS, pmath_cos);
    fallback_cosh = Psyco_DefineModuleFn(md, "cosh", METH_VARARGS, pmath_cosh);
    fallback_exp  = Psyco_DefineModuleFn(md, "exp",  METH_VARARGS, pmath_exp);
    fallback_fabs = Psyco_DefineModuleFn(md, "fabs", METH_VARARGS, pmath_fabs);
    fallback_floor= Psyco_DefineModuleFn(md, "floor",METH_VARARGS, pmath_floor);
    fallback_fmod = Psyco_DefineModuleFn(md, "fmod", METH_VARARGS, pmath_fmod);
    fallback_hypot= Psyco_DefineModuleFn(md, "hypot",METH_VARARGS, pmath_hypot);
    /*Psyco_DefineModuleFn(md, "power", METH_VARARGS, pmath_power);*/
    fallback_pow  = Psyco_DefineModuleFn(md, "pow",  METH_VARARGS, pmath_pow);
    fallback_sin  = Psyco_DefineModuleFn(md, "sin",  METH_VARARGS, pmath_sin);
    fallback_sinh = Psyco_DefineModuleFn(md, "sinh", METH_VARARGS, pmath_sinh);
    fallback_sqrt = Psyco_DefineModuleFn(md, "sqrt", METH_VARARGS, pmath_sqrt);
    fallback_tan  = Psyco_DefineModuleFn(md, "tan",  METH_VARARGS, pmath_tan);
    fallback_tanh = Psyco_DefineModuleFn(md, "tanh", METH_VARARGS, pmath_tanh);

    Py_XDECREF(md);
}

#else /* !HAVE_FP_FN_CALLS */
INITIALIZATIONFN
void psyco_initmath(void)
{
}
#endif /* !HAVE_FP_FN_CALLS */
