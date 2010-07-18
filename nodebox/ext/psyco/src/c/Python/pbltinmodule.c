#include "pbltinmodule.h"
#include "../Objects/pintobject.h"
#include "../Objects/ptupleobject.h"
#include "../Objects/plistobject.h"
#include "../Objects/pstringobject.h"
#include "../Objects/prangeobject.h"


static PyCFunction cimpl_range;
static PyCFunction cimpl_xrange;
static PyCFunction cimpl_chr;
static PyCFunction cimpl_ord;
static PyCFunction cimpl_id;
static PyCFunction cimpl_len;
static PyCFunction cimpl_abs;
static PyCFunction cimpl_apply;
static PyCFunction cimpl_divmod;


static vinfo_t* get_len_of_range(PsycoObject* po, vinfo_t* lo, vinfo_t* hi
				 /*, vinfo_t* step == 1 currently*/)
{
	/* translated from bltinmodule.c */
	condition_code_t cc = integer_cmp(po, lo, hi, Py_LT);
	if (cc == CC_ERROR)
		return NULL;
	if (runtime_condition_t(po, cc)) {
		vinfo_t* vresult = integer_sub(po, hi, lo, false);
		assert_nonneg(vresult);
		return vresult;
	}
	else
		return psyco_vi_Zero();
}

static vinfo_t* intobj_as_long(PsycoObject* po, vinfo_t* v)
{
	if (Psyco_VerifyType(po, v, &PyInt_Type) == 1)
		return PsycoInt_AS_LONG(po, v);
	else
		return NULL;
}

static bool parse_range_args(PsycoObject* po, vinfo_t* vargs,
			     vinfo_t** iistart, vinfo_t** iilen)
{
	vinfo_t* ilow;
	vinfo_t* ihigh;
	int tuplesize = PsycoTuple_Load(vargs);  /* -1 if unknown */
	
	switch (tuplesize) {
	case 1:
		ihigh = intobj_as_long(po, PsycoTuple_GET_ITEM(vargs, 0));
		if (ihigh == NULL) return false;
		ilow = psyco_vi_Zero();
		vinfo_incref(ihigh);
		break;
	/*case 3:
		istep = intobj_as_long(po, PsycoTuple_GET_ITEM(vargs, 2));
		if (istep == NULL) return NULL;*/
		/* fall through */
	case 2:
		ilow  = intobj_as_long(po, PsycoTuple_GET_ITEM(vargs, 0));
		if (ilow == NULL) return false;
		ihigh = intobj_as_long(po, PsycoTuple_GET_ITEM(vargs, 1));
		if (ihigh == NULL) return false;
		vinfo_incref(ilow);
		vinfo_incref(ihigh);
		break;
	default:
		return false;
	}
	*iilen = get_len_of_range(po, ilow, ihigh);
	vinfo_decref(ihigh, po);
	if (*iilen == NULL) {
		vinfo_decref(ilow, po);
		return false;
	}
	*iistart = ilow;
	return true;
}

static vinfo_t* pbuiltin_range(PsycoObject* po, vinfo_t* vself, vinfo_t* vargs)
{
	vinfo_t* istart;
	vinfo_t* ilen;
	if (parse_range_args(po, vargs, &istart, &ilen)) {
		return PsycoListRange_NEW(po, istart, ilen);
	}
	if (PycException_Occurred(po))
		return NULL;
	return psyco_generic_call(po, cimpl_range,
				  CfReturnRef|CfPyErrIfNull,
				  "lv", NULL, vargs);
}

static vinfo_t* pbuiltin_xrange(PsycoObject* po, vinfo_t* vself, vinfo_t* vargs)
{
	vinfo_t* istart;
	vinfo_t* ilen;
	if (parse_range_args(po, vargs, &istart, &ilen)) {
		return PsycoXRange_NEW(po, istart, ilen);
	}
	if (PycException_Occurred(po))
		return NULL;
	return psyco_generic_call(po, cimpl_xrange,
				  CfReturnRef|CfPyErrIfNull,
				  "lv", NULL, vargs);
}

static vinfo_t* prange_new(PsycoObject* po, PyTypeObject* type,
			   vinfo_t* vargs, vinfo_t* vkw)
{
	/* for Python >= 2.3, where __builtin__.xrange is a type */
	vinfo_t* istart;
	vinfo_t* ilen;
	psyco_assert(type == &PyRange_Type);   /* no subclassing xrange */
	if (parse_range_args(po, vargs, &istart, &ilen)) {
		return PsycoXRange_NEW(po, istart, ilen);
	}
	if (PycException_Occurred(po))
		return NULL;
	return psyco_generic_call(po, type->tp_new,
				  CfReturnRef|CfPyErrIfNull,
				  "lvv", type, vargs, vkw);
}

static vinfo_t* pbuiltin_chr(PsycoObject* po, vinfo_t* vself, vinfo_t* vargs)
{
	vinfo_t* intval;
	vinfo_t* result;
	condition_code_t cc;
	
	if (PsycoTuple_Load(vargs) != 1)
		goto use_proxy;
	intval = PsycoInt_AsLong(po, PsycoTuple_GET_ITEM(vargs, 0));
	if (intval == NULL)
		return NULL;

	cc = integer_cmp_i(po, intval, 255, Py_GT|COMPARE_UNSIGNED);
	if (cc == CC_ERROR) {
		vinfo_decref(intval, po);
		return NULL;
	}
	if (runtime_condition_f(po, cc)) {
		vinfo_decref(intval, po);
		goto use_proxy;
	}

	result = PsycoCharacter_New(intval);
	vinfo_decref(intval, po);
	return result;

   use_proxy:
	return psyco_generic_call(po, cimpl_chr, CfReturnRef|CfPyErrIfNull,
				  "lv", NULL, vargs);
}

static vinfo_t* pbuiltin_ord(PsycoObject* po, vinfo_t* vself, vinfo_t* vobj)
{
	vinfo_t* result;
	if (!PsycoCharacter_Ord(po, vobj, &result))
		return NULL;
	
	if (result != NULL)
		return PsycoInt_FROM_LONG(result);
	
	return psyco_generic_call(po, cimpl_ord, CfReturnRef|CfPyErrIfNull,
				  "lv", NULL, vobj);
}

static vinfo_t* pbuiltin_id(PsycoObject* po, vinfo_t* vself, vinfo_t* vobj)
{
#if HAVE_NEGATIVE_IDS   /* Python < 2.5 */
	return PsycoInt_FromLong(vobj);
#else
	/* XXX fall-back for now */
	return psyco_generic_call(po, PyLong_FromVoidPtr,
				  CfReturnRef|CfPyErrIfNull,
				  "v", vobj);
#endif
}

static vinfo_t* pbuiltin_len(PsycoObject* po, vinfo_t* vself, vinfo_t* vobj)
{
	vinfo_t* result;
	result = PsycoObject_Size(po, vobj);
	if (result != NULL)
		result = PsycoInt_FROM_LONG(result);
	return result;
}

static vinfo_t* pbuiltin_abs(PsycoObject* po, vinfo_t* vself, vinfo_t* vobj)
{
	return PsycoNumber_Absolute(po, vobj);
}

static vinfo_t* pbuiltin_apply(PsycoObject* po, vinfo_t* vself, vinfo_t* vargs)
{
	vinfo_t* alist = NULL;
	vinfo_t* kwdict = NULL;
	vinfo_t* retval;
	int tuplesize = PsycoTuple_Load(vargs);  /* -1 if unknown */
	PyTypeObject* argt;
	vinfo_t* t = NULL;

	switch (tuplesize) {
	case 3:
		kwdict = PsycoTuple_GET_ITEM(vargs, 2);
		if (Psyco_VerifyType(po, kwdict, &PyDict_Type) != true) {
			/* 'kwdict' is not a dictionary */
			break;
		}
		/* fall through */
	case 2:
		alist = PsycoTuple_GET_ITEM(vargs, 1);
		argt = Psyco_NeedType(po, alist);
		if (argt == NULL)
			return NULL;
		if (!PyType_TypeCheck(argt, &PyTuple_Type)) {
			/* 'alist' is not a tuple */
			if (!PsycoSequence_Check(argt))
				break;  /* give up */
			t = PsycoSequence_Tuple(po, alist);
			if (t == NULL)
				break;  /* give up */
			alist = t;
		}
		/* fall through */
	case 1:
		retval = PsycoEval_CallObjectWithKeywords(po,
					PsycoTuple_GET_ITEM(vargs, 0),
					alist, kwdict);
		vinfo_xdecref(t, po);
		return retval;
	}

	if (PycException_Occurred(po))
		return NULL;
	return psyco_generic_call(po, cimpl_apply, CfReturnRef|CfPyErrIfNull,
				  "lv", NULL, vargs);
}

static vinfo_t* pbuiltin_divmod(PsycoObject* po, vinfo_t* vself, vinfo_t* vargs)
{
	int tuplesize = PsycoTuple_Load(vargs);  /* -1 if unknown */
	
	if (tuplesize == 2) {
		return PsycoNumber_Divmod(po,
					  PsycoTuple_GET_ITEM(vargs, 0),
					  PsycoTuple_GET_ITEM(vargs, 1));
	}
	return psyco_generic_call(po, cimpl_divmod, CfReturnRef|CfPyErrIfNull,
				  "lv", NULL, vargs);
}


/***************************************************************/


INITIALIZATIONFN
void psyco_bltinmodule_init(void)
{
	PyObject* md = Psyco_DefineMetaModule("__builtin__");

#define DEFMETA(name, flags)							\
    cimpl_ ## name = Psyco_DefineModuleFn(md, #name, flags, &pbuiltin_ ## name)

	DEFMETA( range,		METH_VARARGS );
	DEFMETA( chr,		METH_VARARGS );
	DEFMETA( ord,		METH_O);
	DEFMETA( id,		METH_O);
	DEFMETA( len,		METH_O);
	DEFMETA( abs,		METH_O);
	DEFMETA( apply,		METH_VARARGS );
	DEFMETA( divmod,	METH_VARARGS );
	cimpl_xrange = Psyco_DefineModuleC(md, "xrange", METH_VARARGS,
                                           &pbuiltin_xrange, prange_new);
#undef DEFMETA
	Py_XDECREF(md);
}
