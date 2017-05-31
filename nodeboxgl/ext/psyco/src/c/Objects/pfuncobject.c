#include "../psyfunc.h"
#include "pfuncobject.h"
#include "pclassobject.h"


 /***************************************************************/
  /***   Virtual functions                                     ***/

static source_virtual_t psyco_computed_function;

static bool compute_function(PsycoObject* po, vinfo_t* v)
{
	vinfo_t* newobj;
	vinfo_t* fcode;
	vinfo_t* fglobals;
	vinfo_t* fdefaults;

	fcode = vinfo_getitem(v, iFUNC_CODE);
	if (fcode == NULL)
		return false;

	fglobals = vinfo_getitem(v, iFUNC_GLOBALS);
	if (fglobals == NULL)
		return false;

	fdefaults = vinfo_getitem(v, iFUNC_DEFAULTS);
	if (fdefaults == NULL)
		return false;

	newobj = psyco_generic_call(po, PyFunction_New,
				    CfReturnRef|CfPyErrIfNull,
				    "vv", fcode, fglobals);
	if (newobj == NULL)
		return false;

	if (!psyco_knowntobe(fdefaults, (long) NULL)) {
		if (!psyco_generic_call(po, PyFunction_SetDefaults,
					CfNoReturnValue|CfPyErrIfNonNull,
					"vv", newobj, fdefaults))
			return false;
	}
	
	/* move the resulting non-virtual Python object back into 'v' */
	vinfo_move(po, v, newobj);
	return true;
}

#if 0	/* not needed currently */
static PyObject* direct_compute_function(vinfo_t* v, char* data)
{
	PyObject* fcode;
	PyObject* fglobals;
	PyObject* fdefaults;
	PyObject* result = NULL;

	fcode     = direct_xobj_vinfo(vinfo_getitem(v, iFUNC_CODE),     data);
	fglobals  = direct_xobj_vinfo(vinfo_getitem(v, iFUNC_GLOBALS),  data);
	fdefaults = direct_xobj_vinfo(vinfo_getitem(v, iFUNC_DEFAULTS), data);

	if (!PyErr_Occurred() && fcode != NULL && fglobals != NULL) {
		result = PyFunction_New(fcode, fglobals);
		if (result != NULL && fdefaults != NULL) {
			if (PyFunction_SetDefaults(result, fdefaults) != 0) {
				Py_DECREF(result);
				result = NULL;
			}
		}
	}
	Py_XDECREF(fdefaults);
	Py_XDECREF(fglobals);
	Py_XDECREF(fcode);
	return result;
}
#endif


DEFINEFN
vinfo_t* PsycoFunction_New(PsycoObject* po, vinfo_t* fcode,
			   vinfo_t* fglobals, vinfo_t* fdefaults)
{
	vinfo_t* r;
	
	/* fdefaults contains potential arguments; mutable objects there
	   must be forced out of virtual-time right now */
	if (fdefaults != NULL && !psyco_forking(po, fdefaults->array))
		return NULL;

	/* Build a virtual function object */
	r = vinfo_new(VirtualTime_New(&psyco_computed_function));
	r->array = array_new(FUNC_TOTAL);
	r->array->items[iOB_TYPE] =
		vinfo_new(CompileTime_New((long)(&PyFunction_Type)));
	vinfo_incref(fcode);
	r->array->items[iFUNC_CODE] = fcode;
	vinfo_incref(fglobals);
	r->array->items[iFUNC_GLOBALS] = fglobals;
	if (fdefaults == NULL)
		fdefaults = psyco_vi_Zero();
	else
		vinfo_incref(fdefaults);
	r->array->items[iFUNC_DEFAULTS] = fdefaults;
	return r;
}


 /***************************************************************/
  /*** function objects meta-implementation                    ***/

DEFINEFN
vinfo_t* pfunction_simple_call(PsycoObject* po, PyObject* f,
                               vinfo_t* arg, bool allow_inline)
{
	PyObject* glob;
	PyObject* defl;
	PyCodeObject* co;
	vinfo_t* fglobals;
	vinfo_t* fdefaults;
	vinfo_t* result;
	int saved_inlining;

	/* XXX we capture the code object, so this breaks if someone
	   changes the .func_code attribute of the function later */
	co = (PyCodeObject*) PyFunction_GET_CODE(f);
	if (PyCode_GetNumFree(co) > 0)
		goto fallback;
	
	glob = PyFunction_GET_GLOBALS(f);
	defl = PyFunction_GET_DEFAULTS(f);
	Py_INCREF(glob);
	fglobals = vinfo_new(CompileTime_NewSk(sk_new
					       ((long)glob, SkFlagPyObj)));
	if (defl == NULL)
		fdefaults = psyco_vi_Zero();
	else {
		Py_INCREF(defl);
		fdefaults = vinfo_new(CompileTime_NewSk(sk_new
						     ((long)defl, SkFlagPyObj)));
	}

	saved_inlining = po->pr.is_inlining;
	if (!allow_inline)
		po->pr.is_inlining = true;
	result = psyco_call_pyfunc(po, co, fglobals, fdefaults,
				   arg, po->pr.auto_recursion);
	po->pr.is_inlining = saved_inlining;
	vinfo_decref(fdefaults, po);
	vinfo_decref(fglobals, po);
	return result;

 fallback:
	return psyco_generic_call(po, PyFunction_Type.tp_call,
				  CfReturnRef|CfPyErrIfNull,
				  "lvl", (long) f, arg, 0);
}

DEFINEFN
vinfo_t* pfunction_call(PsycoObject* po, vinfo_t* func,
                        vinfo_t* arg, vinfo_t* kw)
{
	if (!psyco_knowntobe(kw, (long) NULL))
		goto fallback;

	if (!is_virtualtime(func->source)) {
		/* run-time or compile-time values: promote the
		   function object as a whole into compile-time */
		PyObject* f;
		switch (psyco_pyobj_atcompiletime_mega(po, func, &f)) {

		case 1: /* promotion ok */
			return pfunction_simple_call(po, f, arg, true);

		case 0: /* megamorphic site */
			goto fallback;   /* XXX could do better */

		default:
			return NULL;
		}
	}
	else {	/* virtual-time function objects: read the
		   individual components */
		PyCodeObject* co;
		vinfo_t* fcode;
		vinfo_t* fglobals;
		vinfo_t* fdefaults;

		fcode = vinfo_getitem(func, iFUNC_CODE);
		if (fcode == NULL)
			return NULL;
		co = (PyCodeObject*)psyco_pyobj_atcompiletime(po, fcode);
		if (co == NULL)
			return NULL;
			
		fglobals = vinfo_getitem(func, iFUNC_GLOBALS);
		if (fglobals == NULL)
			return NULL;
			
		fdefaults = vinfo_getitem(func, iFUNC_DEFAULTS);
		if (fdefaults == NULL)
			return NULL;

		return psyco_call_pyfunc(po, co, fglobals, fdefaults,
					 arg, po->pr.auto_recursion);
	}

 fallback:

	return psyco_generic_call(po, PyFunction_Type.tp_call,
				  CfReturnRef|CfPyErrIfNull,
				  "vvv", func, arg, kw);
}


static vinfo_t* pfunc_descr_get(PsycoObject* po, PyObject* func,
				vinfo_t* obj, PyObject* type)
{
	/* see comments of pmember_get() in pdescrobject.c. */

	/* XXX obj is never Py_None here in the current implementation,
	   but could be if called by other routines than
	   PsycoObject_GenericGetAttr(). */
	return PsycoMethod_New(func, obj, type);
}


INITIALIZATIONFN
void psy_funcobject_init(void)
{
	Psyco_DefineMeta(PyFunction_Type.tp_call, pfunction_call);
	Psyco_DefineMeta(PyFunction_Type.tp_descr_get, pfunc_descr_get);

        /* function object are mutable;
           they must be forced out of virtual-time across function calls */
        INIT_SVIRTUAL_NOCALL(psyco_computed_function, compute_function, 1);
}
