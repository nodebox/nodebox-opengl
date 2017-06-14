#include "../psyco.h"
#include "../mergepoints.h"
#include "../Objects/ptupleobject.h"
#include "../Objects/pdictobject.h"


static PyCFunction cimpl_globals;
static PyCFunction cimpl_eval;
static PyCFunction cimpl_execfile;
static PyCFunction cimpl_locals;
static PyCFunction cimpl_vars;
static PyCFunction cimpl_dir;
static PyCFunction cimpl_input;

/***************************************************************/
 /***   Psyco meta-version of functions accessing the locals  ***/

PSY_INLINE bool psyco_fast_locals_ok(PsycoObject* po)
{
	return !(psyco_mp_flags(po->pr.merge_points) & MP_FLAGS_CONTROLFLOW);
}

static vinfo_t* psyco_fast_to_locals(PsycoObject* po)
{
	int j;
	PyObject* map;
	PyCodeObject* co = po->pr.co;
	vinfo_t* vlocals = PsycoDict_New(po);
	if (vlocals == NULL)
		return NULL;

	map = co->co_varnames;
	if (!PyTuple_Check(map))
		return vlocals;
	j = PyTuple_GET_SIZE(map);
	if (j > co->co_nlocals)
		j = co->co_nlocals;

	while (--j >= 0) {
		PyObject *key = PyTuple_GET_ITEM(map, j);
		vinfo_t* vvalue = LOC_LOCALS_PLUS[j];
		/* a local variable can only be unbound if its
		   value is known to be (PyObject*)NULL. A run-time
		   or virtual value is always non-NULL. */
		if (!psyco_knowntobe(vvalue, 0)) {
			if (!PsycoDict_SetItem(po, vlocals, key, vvalue)) {
				vinfo_decref(vlocals, po);
				return NULL;
			}
		}
	}
	return vlocals;
}

static PyObject* fast_to_locals_keys(PsycoObject* po)
{
	int j;
	PyObject* map;
	PyCodeObject* co = po->pr.co;
	PyObject* keys = PyList_New(0);
	if (keys == NULL)
		return NULL;

	map = co->co_varnames;
	if (!PyTuple_Check(map))
		return keys;
	j = PyTuple_GET_SIZE(map);
	if (j > co->co_nlocals)
		j = co->co_nlocals;

	while (--j >= 0) {
		PyObject *key = PyTuple_GET_ITEM(map, j);
		vinfo_t* vvalue = LOC_LOCALS_PLUS[j];
		/* a local variable can only be unbound if its
		   value is known to be (PyObject*)NULL. A run-time
		   or virtual value is always non-NULL. */
		if (!psyco_knowntobe(vvalue, 0)) {
			if (PyList_Append(keys, key) < 0) {
				Py_DECREF(keys);
				return NULL;
			}
		}
	}
	if (PyList_Sort(keys) < 0) {
		Py_DECREF(keys);
		return NULL;
	}
	return keys;
}

static vinfo_t* pget_cpsyco_obj(char* name)
{
	PyObject* d = PyModule_GetDict(CPsycoModule);
	PyObject* result = PyDict_GetItemString(d, name);
	if (result == NULL)
		return NULL;
	else
		return vinfo_new(CompileTime_New((long) result));
}

static vinfo_t* ppsyco_globals(PsycoObject* po, vinfo_t* vself, vinfo_t* vargs)
{
	if (PsycoTuple_Load(vargs) == 0) {
		vinfo_t* vglobals = LOC_GLOBALS;
		vinfo_incref(vglobals);
		return vglobals;
	}
	return psyco_generic_call(po, cimpl_globals,
				  CfReturnRef|CfPyErrIfNull,
				  "vv", vself, vargs);
}

static vinfo_t* pbuiltinevaluator(PsycoObject* po, vinfo_t* vargs,
				  char* original_name, PyCFunction cimpl)
{
	vinfo_t* vfn;
	vinfo_t* var;
	vinfo_t* vkw;
	vinfo_t* vresult = NULL;
	vinfo_t* args[3];

	if (!psyco_fast_locals_ok(po) || PsycoTuple_Load(vargs) != 1)
		goto fallback;

	vfn = pget_cpsyco_obj(original_name);
	if (vfn == NULL)
		goto fallback;

	args[0] = PsycoTuple_GET_ITEM(vargs, 0);
	args[1] = LOC_GLOBALS;
	args[2] = psyco_fast_to_locals(po);
	if (args[2] == NULL)
		goto error;

	var = PsycoTuple_New(3, args);
	vkw = psyco_vi_Zero();
	vresult = PsycoObject_Call(po, vfn, var, vkw);
	vinfo_decref(vkw, po);
	vinfo_decref(var, po);
	vinfo_decref(args[2], po);
   error:
	vinfo_decref(vfn, po);
	return vresult;

   fallback:
	return psyco_generic_call(po, cimpl, CfReturnRef|CfPyErrIfNull,
				  "lv", (long) NULL, vargs);
}

static vinfo_t* ppsyco_eval(PsycoObject* po, vinfo_t* vself, vinfo_t* vargs)
{
	return pbuiltinevaluator(po, vargs, "original_eval", cimpl_eval);
}

static vinfo_t* ppsyco_execfile(PsycoObject* po, vinfo_t* vself, vinfo_t* vargs)
{
	return pbuiltinevaluator(po, vargs, "original_execfile", cimpl_execfile);
}

static vinfo_t* ppsyco_locals(PsycoObject* po, vinfo_t* vself, vinfo_t* vargs)
{
	if (psyco_fast_locals_ok(po) && PsycoTuple_Load(vargs) == 0) {
		return psyco_fast_to_locals(po);
	}
	return psyco_generic_call(po, cimpl_locals,
				  CfReturnRef|CfPyErrIfNull,
				  "vv", vself, vargs);
}

static vinfo_t* ppsyco_vars(PsycoObject* po, vinfo_t* vself, vinfo_t* vargs)
{
	if (psyco_fast_locals_ok(po) && PsycoTuple_Load(vargs) == 0) {
		return psyco_fast_to_locals(po);
	}
	return psyco_generic_call(po, cimpl_vars,
				  CfReturnRef|CfPyErrIfNull,
				  "vv", vself, vargs);
}

static vinfo_t* ppsyco_dir(PsycoObject* po, vinfo_t* vself, vinfo_t* vargs)
{
	if (psyco_fast_locals_ok(po) && PsycoTuple_Load(vargs) == 0) {
		PyObject* keys = fast_to_locals_keys(po);
		if (keys == NULL) {
			psyco_virtualize_exception(po);
			return NULL;
		}
		return vinfo_new(CompileTime_NewSk(sk_new((long) keys,
							  SkFlagPyObj)));
	}
	return psyco_generic_call(po, cimpl_dir,
				  CfReturnRef|CfPyErrIfNull,
				  "vv", vself, vargs);
}

static vinfo_t* ppsyco_input(PsycoObject* po, vinfo_t* vself, vinfo_t* vargs)
{
	vinfo_t* vfn;
	vinfo_t* vkw;
	vinfo_t* vcmd;
	vinfo_t* vresult;

	vfn = pget_cpsyco_obj("original_raw_input");
	if (vfn == NULL)
		goto fallback;

	vkw = psyco_vi_Zero();
	vcmd = PsycoObject_Call(po, vfn, vargs, vkw);
	vinfo_decref(vkw, po);
	vinfo_decref(vfn, po);
	if (vcmd == NULL)
		return NULL;

	vargs = PsycoTuple_New(1, &vcmd);
	vresult = ppsyco_eval(po, NULL, vargs);
	vinfo_decref(vargs, po);
	vinfo_decref(vcmd, po);
	return vresult;

   fallback:
	return psyco_generic_call(po, cimpl_input,
				  CfReturnRef|CfPyErrIfNull,
				  "vv", vself, vargs);
}

/***************************************************************/


INITIALIZATIONFN
void psyco_initpsyco(void)
{
	PyObject* md = CPsycoModule;

#define DEFMETA(name)							\
    cimpl_ ## name = Psyco_DefineModuleFn(md, #name, METH_VARARGS,	\
                                          &ppsyco_ ## name)

	DEFMETA( globals );
	DEFMETA( eval );
	DEFMETA( execfile );
	DEFMETA( locals );
	DEFMETA( vars );
	DEFMETA( dir );
	DEFMETA( input );

#undef DEFMETA
}
