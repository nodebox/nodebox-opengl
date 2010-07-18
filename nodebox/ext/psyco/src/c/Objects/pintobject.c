#include "pintobject.h"
#include "plongobject.h"


/* Division and Modulo code follows Python's intobject.c */
static long cimpl_int_mod(long x, long y)
{
	long xmody;
	/* (-sys.maxint-1)/-1 is the only overflow case. */
	if (y == 0 || (y == -1 && x == LONG_MIN)) {
		/* the exception will be cleared by the caller */
		PyErr_SetString(PyExc_ValueError, "punt and do this in python code");
		return -1;
	}
	xmody = x % y;
	if (xmody && ((y ^ xmody) < 0) /* i.e. and signs differ */) {
		xmody += y;
	}
	return xmody;
}

static long cimpl_int_div(long x, long y)
{
	long xdivy;
	long xmody;
	/* (-sys.maxint-1)/-1 is the only overflow case. */
	if (y == 0 || (y == -1 && x == LONG_MIN)) {
		/* the exception will be cleared by the caller */
		PyErr_SetString(PyExc_ValueError, "punt and do this in python code");
		return -1;
	}
	xdivy = x / y;
	xmody = x - xdivy * y;
	if (xmody && ((y ^ xmody) < 0) /* i.e. and signs differ */) {
		--xdivy;
	}
	return xdivy;
}

static long cimpl_int_pow2_nonneg(long iv, long iw)
{
	long ix, prev, temp;
	extra_assert(iw >= 0);
	/* code from Python 2.5 */
 	temp = iv;
	ix = 1;
	while (iw > 0) {
	 	prev = ix;	/* Save value for overflow check */
	 	if (iw & 1) {
		 	ix = ix*temp;
			if (temp == 0)
				break; /* Avoid ix / 0 */
			if (ix / temp != prev)
				goto overflow;
		}
	 	iw >>= 1;	/* Shift exponent down by 1 bit */
	        if (iw==0) break;
	 	prev = temp;
	 	temp *= temp;	/* Square the value of temp */
	 	if (prev != 0 && temp / prev != prev)
			goto overflow;
	}
	return ix;

 overflow:
	/* the exception will be cleared by the caller */
	PyErr_SetString(PyExc_OverflowError, "punt and do this in python code");
	return -1;
}

static long cimpl_int_pow2(long iv, long iw)
{
	if (iw < 0) {
		/* the exception will be cleared by the caller */
		PyErr_SetString(PyExc_ValueError,
				"punt and do this in python code");
		return -1;
	}
	return cimpl_int_pow2_nonneg(iv, iw);
}

DEFINEFN
vinfo_t* PsycoInt_AsLong(PsycoObject* po, vinfo_t* v)
{
	vinfo_t* result;
	PyNumberMethods *nb;
	PyTypeObject* tp;
	
	tp = Psyco_NeedType(po, v);
	if (tp == NULL)
		return NULL;

	if (PsycoInt_Check(tp)) {
		result = PsycoInt_AS_LONG(po, v);
		if (result != NULL)
			vinfo_incref(result);
		return result;
	}

	if ((nb = tp->tp_as_number) == NULL || nb->nb_int == NULL) {
		PycException_SetString(po, PyExc_TypeError,
				       "an integer is required");
		return NULL;
	}

	return psyco_generic_call(po, PyInt_AsLong,
				  CfReturnNormal|CfPyErrCheckMinus1,
				  "v", v);
#if 0
	---  DISABLED: cannot promote the type of a returned object :-(  ---
	v = Psyco_META1(po, nb->nb_int,
			CfReturnRef|CfPyErrIfNull,
			"v", v);
	if (v == NULL)
		return NULL;

	/* check the returned type */
	result = NULL;
	tp = Psyco_NeedType(po, v);
	if (tp != NULL) {
		if (PsycoInt_Check(tp)) {
			result = PsycoInt_AS_LONG(po, v);
			if (result != NULL)
				vinfo_incref(result);
		}
		else if (PsycoLong_Check(tp)) {
			result = PsycoLong_AsLong(po, v);
		}
		else {  /* fall back */
			result = psyco_generic_call(po, PyInt_AsLong,
					CfReturnNormal|CfPyErrCheckMinus1,
					"v", v);
		}
	}
	vinfo_decref(v, po);
	return result;
#endif
}

static bool compute_int(PsycoObject* po, vinfo_t* intobj)
{
	vinfo_t* newobj;
	vinfo_t* x;
	
	/* get the field 'ob_ival' from the Python object 'intobj' */
	x = vinfo_getitem(intobj, iINT_OB_IVAL);
	if (x == NULL)
		return false;

	/* call PyInt_FromLong() */
	newobj = psyco_generic_call(po, PyInt_FromLong,
				    CfPure|CfReturnRef|CfPyErrIfNull, "v", x);
	if (newobj == NULL)
		return false;

	/* move the resulting non-virtual Python object back into 'intobj' */
	vinfo_move(po, intobj, newobj);
	return true;
}

static PyObject* direct_compute_int(vinfo_t* intobj, char* data)
{
	int ival;
	ival = direct_read_vinfo(vinfo_getitem(intobj, iINT_OB_IVAL), data);
	if (ival == -1 && PyErr_Occurred())
		return NULL;
	return PyInt_FromLong(ival);
}


DEFINEVAR source_virtual_t psyco_computed_int;


 /***************************************************************/
  /*** integer objects meta-implementation                     ***/

static vinfo_t* pint_nonzero(PsycoObject* po, vinfo_t* intobj)
{
	vinfo_t* ival = PsycoInt_AS_LONG(po, intobj);
	condition_code_t cc = integer_non_null(po, ival);
	if (cc == CC_ERROR)
		return NULL;
	return psyco_vinfo_condition(po, cc);
}

static vinfo_t* pint_pos(PsycoObject* po, vinfo_t* intobj)
{
	if (Psyco_KnownType(intobj) == &PyInt_Type) {
		vinfo_incref(intobj);
		return intobj;
	}
	else {
		vinfo_t* ival = PsycoInt_AS_LONG(po, intobj);
		if (ival == NULL)
			return NULL;
		return PsycoInt_FromLong(ival);
	}
}

static vinfo_t* pint_neg(PsycoObject* po, vinfo_t* intobj)
{
	vinfo_t* result;
	vinfo_t* ival = PsycoInt_AS_LONG(po, intobj);
	if (ival == NULL)
		return NULL;
	result = integer_neg(po, ival, true);
	if (result != NULL)
		return PsycoInt_FROM_LONG(result);
	
	if (PycException_Occurred(po))
		return NULL;
	/* overflow */
	return psyco_generic_call(po, PyInt_Type.tp_as_number->nb_negative,
				  CfPure|CfReturnRef|CfPyErrIfNull,
				  "v", intobj);
}

static vinfo_t* pint_invert(PsycoObject* po, vinfo_t* intobj)
{
	vinfo_t* result;
	vinfo_t* ival = PsycoInt_AS_LONG(po, intobj);
	if (ival == NULL)
		return NULL;
	result = integer_inv(po, ival);
	if (result != NULL)
		result = PsycoInt_FROM_LONG(result);
	return result;
}

static vinfo_t* pint_abs(PsycoObject* po, vinfo_t* intobj)
{
	vinfo_t* result;
	vinfo_t* ival = PsycoInt_AS_LONG(po, intobj);
	if (ival == NULL)
		return NULL;
	result = integer_abs(po, ival, true);
	if (result != NULL)
		return PsycoInt_FROM_LONG(result);
	
	if (PycException_Occurred(po))
		return NULL;
	/* overflow */
	return psyco_generic_call(po, PyInt_Type.tp_as_number->nb_absolute,
				  CfPure|CfReturnRef|CfPyErrIfNull,
				  "v", intobj);
}


#define CONVERT_TO_LONG(vobj, vlng)				\
	switch (Psyco_VerifyType(po, vobj, &PyInt_Type)) {	\
	case true:   /* vobj is a PyIntObject */		\
		vlng = PsycoInt_AS_LONG(po, vobj);		\
		if (vlng == NULL)				\
			return NULL;				\
		break;						\
	case false:  /* vobj is not a PyIntObject */		\
		return psyco_vi_NotImplemented();		\
	default:     /* error or promotion */			\
		return NULL;					\
	}

static vinfo_t* pint_add(PsycoObject* po, vinfo_t* v, vinfo_t* w)
{
	vinfo_t* a;
	vinfo_t* b;
	vinfo_t* x;
	CONVERT_TO_LONG(v, a);
	CONVERT_TO_LONG(w, b);
	x = integer_add(po, a, b, true);
	if (x != NULL)
		return PsycoInt_FROM_LONG(x);
	if (PycException_Occurred(po))
		return NULL;
	/* overflow */
	return psyco_generic_call(po, PyInt_Type.tp_as_number->nb_add,
				  CfPure|CfReturnRef|CfPyErrIfNull,
				  "vv", v, w);
}

static vinfo_t* pint_sub(PsycoObject* po, vinfo_t* v, vinfo_t* w)
{
	vinfo_t* a;
	vinfo_t* b;
	vinfo_t* x;
	CONVERT_TO_LONG(v, a);
	CONVERT_TO_LONG(w, b);
	x = integer_sub(po, a, b, true);
	if (x != NULL)
		return PsycoInt_FROM_LONG(x);
	if (PycException_Occurred(po))
		return NULL;
	/* overflow */
	return psyco_generic_call(po, PyInt_Type.tp_as_number->nb_subtract,
				  CfPure|CfReturnRef|CfPyErrIfNull,
				  "vv", v, w);
}

static vinfo_t* pint_mod(PsycoObject* po, vinfo_t* v, vinfo_t* w) 
{
	vinfo_t* a;
	vinfo_t* b;
	vinfo_t* x;
	CONVERT_TO_LONG(v, a);
	CONVERT_TO_LONG(w, b);
	x = psyco_generic_call(po, cimpl_int_mod, CfPure|CfReturnNormal|CfPyErrCheckMinus1, "vv", a, b);
	if (x != NULL)
		return PsycoInt_FROM_LONG(x);
	/* Either an error occured or it overflowed. In either case let python deal with it */
	PycException_Clear(po);
	return psyco_generic_call(po, PyInt_Type.tp_as_number->nb_remainder,
				  CfPure|CfReturnRef|CfPyErrIfNull,
				  "vv", v, w);
}

static vinfo_t* pint_div(PsycoObject* po, vinfo_t* v, vinfo_t* w) 
{
	vinfo_t* a;
	vinfo_t* b;
	vinfo_t* x;
	CONVERT_TO_LONG(v, a);
	CONVERT_TO_LONG(w, b);
	x = psyco_generic_call(po, cimpl_int_div, CfPure|CfReturnNormal|CfPyErrCheckMinus1, "vv", a, b);
	if (x != NULL)
		return PsycoInt_FROM_LONG(x);
	/* Either an error occured or it overflowed. In either case let python deal with it */
	PycException_Clear(po);
	return psyco_generic_call(po, PyInt_Type.tp_as_number->nb_divide,
				  CfPure|CfReturnRef|CfPyErrIfNull,
				  "vv", v, w);
}

static vinfo_t* pint_pow(PsycoObject* po, vinfo_t* v, vinfo_t* w, vinfo_t* z)
{
	vinfo_t* a;
	vinfo_t* b;
	vinfo_t* x;
	void* cimpl;
	if (!psyco_knowntobe(z, (long) Py_None)) {
		return psyco_generic_call(po, PyInt_Type.tp_as_number->nb_power,
				CfPure|CfReturnRef|CfPyErrNotImplemented,
					  "vvv", v, w, z);
	}
	CONVERT_TO_LONG(v, a);
	CONVERT_TO_LONG(w, b);
	if (is_nonneg(b->source))
		cimpl = cimpl_int_pow2_nonneg;
	else
		cimpl = cimpl_int_pow2;
	x = psyco_generic_call(po, cimpl,
			       CfPure|CfReturnNormal|CfPyErrCheckMinus1,
			       "vv", a, b);
	if (x != NULL)
		return PsycoInt_FROM_LONG(x);
	/* Either an error occured or it overflowed. In either case let python deal with it */
	PycException_Clear(po);
	return psyco_generic_call(po, PyInt_Type.tp_as_number->nb_power,
				  CfPure|CfReturnRef|CfPyErrIfNull,
				  "vvv", v, w, z);
}

DEFINEFN
vinfo_t* pint_base2op(PsycoObject* po, vinfo_t* v, vinfo_t* w,
                      vinfo_t*(*op)(PsycoObject*,vinfo_t*,vinfo_t*))
{
	vinfo_t* a;
	vinfo_t* b;
	vinfo_t* x;
	CONVERT_TO_LONG(v, a);
	CONVERT_TO_LONG(w, b);
	x = op (po, a, b);
	if (x != NULL)
		x = PsycoInt_FROM_LONG(x);
	return x;
}

static vinfo_t* pint_or(PsycoObject* po, vinfo_t* v, vinfo_t* w)
{
	return pint_base2op(po, v, w, integer_or);
}

static vinfo_t* pint_xor(PsycoObject* po, vinfo_t* v, vinfo_t* w)
{
	return pint_base2op(po, v, w, integer_xor);
}

static vinfo_t* pint_and(PsycoObject* po, vinfo_t* v, vinfo_t* w)
{
	return pint_base2op(po, v, w, integer_and);
}

static vinfo_t* pint_mul(PsycoObject* po, vinfo_t* v, vinfo_t* w)
{
	vinfo_t* a;
	vinfo_t* b;
	vinfo_t* x;
	CONVERT_TO_LONG(v, a);
	CONVERT_TO_LONG(w, b);
	x = integer_mul(po, a, b, true);
	if (x != NULL)
		return PsycoInt_FROM_LONG(x);
	if (PycException_Occurred(po))
		return NULL;
	/* overflow */
	return psyco_generic_call(po, PyInt_Type.tp_as_number->nb_multiply,
				  CfPure|CfReturnRef|CfPyErrIfNull,
				  "vv", v, w);
}

#if PY_VERSION_HEX < 0x02040000

static vinfo_t* pint_lshift(PsycoObject* po, vinfo_t* v, vinfo_t* w)
{
	return pint_base2op(po, v, w, integer_lshift);
}

#else
/* Python 2.4: left shifts can return longs */

static long cimpl_int_lshift(long a, long b)
{
	long c;
	if (b < 0)
		return -1;   /* error */
	if (a == 0)
		return 0;
	if (b >= LONG_BIT)
		return -1;   /* overflow */
	c = a << b;
	if (a != Py_ARITHMETIC_RIGHT_SHIFT(long, c, b))
		return -1;   /* overflow */
	return c;
}

static PyObject* cimpl_ovf_int_lshift(long a, long b)
{
	if (b > 0) {
		/* cimpl_int_lshift() overflowed */
		PyObject *vv, *ww, *result;
		vv = PyLong_FromLong(a);
		if (vv == NULL)
			return NULL;
		ww = PyLong_FromLong(b);
		if (ww == NULL) {
			Py_DECREF(vv);
			return NULL;
		}
		result = PyNumber_Lshift(vv, ww);
		Py_DECREF(vv);
		Py_DECREF(ww);
		return result;
	}
	else if (b == 0) {
		/* special case '(-1)<<0', which makes cimpl_int_lshift()
		   return -1 by accident */
		return PyInt_FromLong(a);
	}
	else {
		PyErr_SetString(PyExc_ValueError, "negative shift count");
		return NULL;
	}
}

static vinfo_t* pint_lshift(PsycoObject* po, vinfo_t* v, vinfo_t* w)
{
	condition_code_t cc;
	vinfo_t* a;
	vinfo_t* b;
	vinfo_t* x;
	CONVERT_TO_LONG(v, a);
	CONVERT_TO_LONG(w, b);
	x = psyco_generic_call(po, cimpl_int_lshift,
			       CfPure|CfReturnNormal,
			       "vv", a, b);
	if (x == NULL)
		return NULL;

	cc = integer_cmp_i(po, x, -1, Py_EQ);
	if (cc == CC_ERROR) {
		vinfo_decref(x, po);
		return NULL;
	}

	if (runtime_condition_f(po, cc)) {
		/* overflow */
		vinfo_decref(x, po);
		return psyco_generic_call(po, cimpl_ovf_int_lshift,
					  CfPure|CfReturnRef|CfPyErrIfNull,
					  "vv", a, b);
	}
	else
		return PsycoInt_FROM_LONG(x);
}

#endif   /* Python 2.4 */

static vinfo_t* pint_rshift(PsycoObject* po, vinfo_t* v, vinfo_t* w)
{
	return pint_base2op(po, v, w, integer_rshift);
}




/* Careful, most operations might return a long if they overflow.
   Only list here the ones that cannot. Besides, all these operations
   should sooner or later be implemented in Psyco. XXX */
/*DEF_KNOWN_RET_TYPE_2(pint_lshift, PyInt_Type.tp_as_number->nb_lshift,
  CfReturnRef|CfPyErrNotImplemented, &PyInt_Type)
  DEF_KNOWN_RET_TYPE_2(pint_rshift, PyInt_Type.tp_as_number->nb_rshift,
  CfReturnRef|CfPyErrNotImplemented, &PyInt_Type)*/

INITIALIZATIONFN
void psy_intobject_init(void)
{
	PyNumberMethods *m = PyInt_Type.tp_as_number;
	Psyco_DefineMeta(m->nb_nonzero,  pint_nonzero);
	
	Psyco_DefineMeta(m->nb_positive, pint_pos);
	Psyco_DefineMeta(m->nb_negative, pint_neg);
	Psyco_DefineMeta(m->nb_invert,   pint_invert);
	Psyco_DefineMeta(m->nb_absolute, pint_abs);
	
	Psyco_DefineMeta(m->nb_add,      pint_add);
	Psyco_DefineMeta(m->nb_subtract, pint_sub);
	Psyco_DefineMeta(m->nb_or,       pint_or);
	Psyco_DefineMeta(m->nb_xor,      pint_xor);
	Psyco_DefineMeta(m->nb_and,      pint_and);
	Psyco_DefineMeta(m->nb_multiply, pint_mul);
	Psyco_DefineMeta(m->nb_lshift,   pint_lshift);
	Psyco_DefineMeta(m->nb_rshift,   pint_rshift);

        /* partial implementations not emitting machine code */
        Psyco_DefineMeta(m->nb_divide,   pint_div);
	Psyco_DefineMeta(m->nb_remainder,pint_mod);
	Psyco_DefineMeta(m->nb_power,    pint_pow);

	INIT_SVIRTUAL(psyco_computed_int, compute_int,
		      direct_compute_int, 0, 0, 0);
}
