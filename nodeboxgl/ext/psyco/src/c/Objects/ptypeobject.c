#include "ptypeobject.h"
#include "ptupleobject.h"
#include "pfuncobject.h"


static ternaryfunc	type_call;
static initproc		object_init;
static newfunc		object_new;
static initproc		slot_tp_init = NULL;

/***************************************************************/
  /*** type objects meta-implementation                        ***/

static int cimpl_call_tp_init(PyTypeObject* type, PyObject* obj,
			      PyObject* args, PyObject* kwds)
{
	/* If the returned object is not an instance of type,
	   it won't be initialized. (Python 2.3 behavior) */
	if (!PyType_IsSubtype(obj->ob_type, type))
		return 0;
	type = obj->ob_type;
	if (PyType_HasFeature(type, Py_TPFLAGS_HAVE_CLASS) &&
	    type->tp_init != NULL)
		return type->tp_init(obj, args, kwds);
	return 0;
}

static vinfo_t* ptype_call(PsycoObject* po, vinfo_t* vtype,
			   vinfo_t* varg, vinfo_t* vkw)
{
	vinfo_t* vobj;
	PyTypeObject* type;
	PyTypeObject* otype;
	type = (PyTypeObject*) psyco_pyobj_atcompiletime(po, vtype);
	if (type == NULL)
		return NULL;
	if (type->tp_new == NULL)
		goto fallback;

	/* Ugly exception: if the call is type(o),
	   just return the type of 'o'. */
	if (type == &PyType_Type) {
		int nb_args;
		if (!psyco_knowntobe(vkw, (long) NULL))
			goto fallback;
		nb_args = PsycoTuple_Load(varg);
		if (nb_args == 1) {
			vinfo_t* v = PsycoTuple_GET_ITEM(varg, 0);
                        return psyco_get_field(po, v, OB_type);
		}
		if (nb_args < 0)
			goto fallback;
	}

	vobj = Psyco_META3(po, type->tp_new,
			   CfReturnRef|CfPyErrIfNull, "lvv",
			   type, varg, vkw);
	if (vobj == NULL)
		return NULL;

	otype = Psyco_KnownType(vobj);
	if (otype == NULL) {
		/* unknown return type, cannot promote it to compile-time
		   now because 'vobj' is not yet stored in 'po->vlocals'.
		   XXX check again why this wouldn't work */
		if (!psyco_generic_call(po, cimpl_call_tp_init,
					CfNoReturnValue|CfPyErrIfNeg,
					"vvvv", vtype, vobj, varg, vkw))
			goto error;
		return vobj;
	}
	
	/* If the returned object is not an instance of type,
	   it won't be initialized. (Python 2.3 behavior) */
	if (PyType_IsSubtype(otype, type) &&
	    PyType_HasFeature(otype, Py_TPFLAGS_HAVE_CLASS) &&
	    otype->tp_init != NULL) {
		if (!Psyco_META3(po, otype->tp_init,
				 CfNoReturnValue|CfPyErrIfNeg,
				 "vvv", vobj, varg, vkw))
			goto error;
	}
	return vobj;

 error:
	vinfo_decref(vobj, po);
	return NULL;

 fallback:
	return psyco_generic_call(po, type_call,
				  CfReturnRef|CfPyErrIfNull,
				  "vvv", vtype, varg, vkw);
}

static int cimpl_check_noarg(PyObject* args, PyObject* kwds)
{
	if ((PyTuple_GET_SIZE(args) ||
	     (kwds && PyDict_Check(kwds) && PyDict_Size(kwds)))) {
		PyErr_SetString(PyExc_TypeError,
				"default __new__ takes no parameters");
		return -1;
	}
	return 0;
}

DEFINEFN
vinfo_t* psyco_pobject_new(PsycoObject* po, PyTypeObject* type,
			   vinfo_t* varg, vinfo_t* vkw)
{
	if (type->tp_init == object_init) {
		/* same rule as in object_new(): check that no argument
		   is passed if type->tp_init == object_init */
		int safe = (psyco_knowntobe(vkw, (long) NULL) &&
			    PsycoTuple_Load(varg) == 0);
		if (!safe && !psyco_generic_call(po, cimpl_check_noarg,
						 CfNoReturnValue|CfPyErrIfNeg,
						 "vv", varg, vkw))
			return NULL;
	}
	return Psyco_META2(po, type->tp_alloc,
			   CfReturnRef|CfPyErrIfNull, "ll",
			   type, 0);
}

static vinfo_t* ptype_genericnew(PsycoObject* po, PyTypeObject* type,
				 vinfo_t* varg, vinfo_t* vkw)
{
	return Psyco_META2(po, type->tp_alloc,
			   CfReturnRef|CfPyErrIfNull, "ll",
			   type, 0);
}

static bool pobject_init(PsycoObject* po, vinfo_t* vself,
			 vinfo_t* vargs, vinfo_t* vkwds)
{
	return true;
}

#define INLINE_GENERIC_ALLOC (PY_VERSION_HEX >= 0x02030000)   /* 2.3 */

#if INLINE_GENERIC_ALLOC
static PyObject* cimpl_alloc_gc_heap(PyTypeObject* type)
{
	size_t size = type->tp_basicsize;
	PyObject* obj = _PyObject_GC_Malloc(size);
	if (obj == NULL)
		return PyErr_NoMemory();
	memset(obj, '\0', size);
	Py_INCREF(type);
	PyObject_INIT(obj, type);
	PyObject_GC_Track(obj);
	return obj;
}

static PyObject* cimpl_alloc_gc_nonheap(PyTypeObject* type)
{
	size_t size = type->tp_basicsize;
	PyObject* obj = _PyObject_GC_Malloc(size);
	if (obj == NULL)
		return PyErr_NoMemory();
	memset(obj, '\0', size);
	PyObject_INIT(obj, type);
	PyObject_GC_Track(obj);
	return obj;
}

static PyObject* cimpl_alloc_nongc_heap(PyTypeObject* type)
{
	size_t size = type->tp_basicsize;
	PyObject* obj = PyObject_MALLOC(size);
	if (obj == NULL)
		return PyErr_NoMemory();
	memset(obj, '\0', size);
	Py_INCREF(type);
	PyObject_INIT(obj, type);
	return obj;
}

static PyObject* cimpl_alloc_nongc_nonheap(PyTypeObject* type)
{
	size_t size = type->tp_basicsize;
	PyObject* obj = PyObject_MALLOC(size);
	if (obj == NULL)
		return PyErr_NoMemory();
	memset(obj, '\0', size);
	PyObject_INIT(obj, type);
	return obj;
}
#endif  /* INLINE_GENERIC_ALLOC */

static vinfo_t* ptype_genericalloc(PsycoObject* po, PyTypeObject* type,
				   int nitems)
{
	vinfo_t* v_result;
#if INLINE_GENERIC_ALLOC
	if (type->tp_itemsize != 0) {
#endif
		/* fallback */
		v_result = psyco_generic_call(po, PyType_GenericAlloc,
					      CfReturnRef|CfPyErrIfNull,
					      "ll", type, nitems);
#if INLINE_GENERIC_ALLOC
	}
	else {
		void* cimpl;
		if (PyType_IS_GC(type)) {
			if (type->tp_flags & Py_TPFLAGS_HEAPTYPE)
				cimpl = cimpl_alloc_gc_heap;
			else
				cimpl = cimpl_alloc_gc_nonheap;
		}
		else {
			if (type->tp_flags & Py_TPFLAGS_HEAPTYPE)
				cimpl = cimpl_alloc_nongc_heap;
			else
				cimpl = cimpl_alloc_nongc_nonheap;
		}
		v_result = psyco_generic_call(po, cimpl,
					      CfReturnRef|CfPyErrIfNull,
					      "l", type);
	}
#endif
	if (v_result != NULL) {
		Psyco_AssertType(po, v_result, type);
	}
	return v_result;
}

/* call a special method in a "safe" way: with inlining turned off and
   without promotion.  See test5.class_creation_2() for why this is needed. */
static vinfo_t* soft_method_call(PsycoObject* po,
				 PyTypeObject* tp, vinfo_t* vself,
				 char* attrstr, PyObject** attrobj,
				 vinfo_t* vargs, vinfo_t* vkwds)
{
	PyObject* descr;
	vinfo_t* v_res;
	vinfo_t* newarg;
	int i, argcount;

	if (*attrobj == NULL) {
		*attrobj = PyString_InternFromString(attrstr);
		if (*attrobj == NULL) {
			psyco_virtualize_exception(po);
			return NULL;
		}
	}

	/* XXX this is broken because the type might have been modified
	   XXX since the last time we were here! */
	descr = _PyType_Lookup(tp, *attrobj);
	if (descr == NULL || !PyFunction_Check(descr))
		return NULL;  /* fallback */

	argcount = PsycoTuple_Load(vargs);
	if (argcount < 0)
		return NULL;  /* fallback */
	if (!psyco_knowntobe(vkwds, (long) NULL))
		return NULL;  /* fallback */

	newarg = PsycoTuple_New(argcount+1, NULL);
	vinfo_incref(vself);
	PsycoTuple_GET_ITEM(newarg, 0) = vself;
	for (i = 0; i < argcount; i++) {
		vinfo_t* v = PsycoTuple_GET_ITEM(vargs, i);
		vinfo_incref(v);
		PsycoTuple_GET_ITEM(newarg, i+1) = v;
	}
	Py_INCREF(descr);
	v_res = pfunction_simple_call(po, descr, newarg, false);
	vinfo_decref(newarg, po);
	return v_res;
}

static bool pslot_tp_init(PsycoObject* po, vinfo_t* vself,
			  vinfo_t* vargs, vinfo_t* vkwds)
{
	static PyObject *init_str;
	vinfo_t* v_res;
	bool ok;
	PyTypeObject* type = Psyco_KnownType(vself);
	if (type == NULL) {
		/* unknown type, cannot promote it to compile-time
		   now because 'vself' is not yet stored in 'po->vlocals'. */
		goto fallback;
	}
	v_res = soft_method_call(po, type, vself, "__init__", &init_str,
				 vargs, vkwds);
	if (v_res == NULL) {
		if (PycException_Occurred(po))
			return false;
		else
			goto fallback;
	}

#if PY_VERSION_HEX >= 0x02050000   /* 2.5 */
	{
		/* check that __init__ returned None */
		condition_code_t cc;
		cc = integer_cmp_i(po, v_res, (long) Py_None, Py_EQ);
		if (cc == CC_ERROR) {
			vinfo_decref(v_res, po);
			return false;
		}
		ok = runtime_condition_t(po, cc);
		vinfo_decref(v_res, po);
		if (!ok) {
			PycException_SetString(po, PyExc_TypeError,
					       "__init__() should return None");
		}
	}
#else
	vinfo_decref(v_res, po);   /* ignore return value */
	ok = true;
#endif
	return ok;

 fallback:
	return psyco_generic_call(po, slot_tp_init,
				  CfNoReturnValue|CfPyErrIfNeg,
				  "vvv", vself, vargs, vkwds) != NULL;
}


INITIALIZATIONFN
void psy_typeobject_init(void)
{
	PyObject* d;
	PyObject* tmp;

	type_call   = PyType_Type.tp_call;
	object_new  = PyBaseObject_Type.tp_new;
	object_init = PyBaseObject_Type.tp_init;
	Psyco_DefineMeta(type_call, ptype_call);
	Psyco_DefineMeta(object_new, psyco_pobject_new);
	Psyco_DefineMeta(object_init, pobject_init);
	Psyco_DefineMeta(PyType_GenericNew, ptype_genericnew);
	Psyco_DefineMeta(PyType_GenericAlloc, ptype_genericalloc);

	/* Any better way to get pointers to the slot_tp_* functions? */
	if (PyErr_Occurred())
		return;
	d = PyDict_New();
	if (d != NULL) {
		char* expr = "type('X', (object,), {'__init__': lambda self: None})";
		tmp = PyRun_String(expr, Py_eval_input, PyEval_GetBuiltins(), d);
		if (tmp && PyType_Check(tmp)) {
			slot_tp_init = ((PyTypeObject*) tmp)->tp_init;
			Psyco_DefineMeta(slot_tp_init, pslot_tp_init);
		}
		Py_XDECREF(tmp);
		Py_DECREF(d);
	}
	PyErr_Clear();
}
