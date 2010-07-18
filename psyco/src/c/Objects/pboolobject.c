#include "pboolobject.h"
#include "pintobject.h"

#if BOOLEAN_TYPE    /* Booleans were introduced in Python 2.3 */


static bool compute_bool(PsycoObject* po, vinfo_t* boolobj)
{
	vinfo_t* newobj;
	vinfo_t* x;
	condition_code_t cc;
	
	/* get the field 'ob_ival' from the Python object 'boolobj' */
	x = vinfo_getitem(boolobj, iBOOL_OB_IVAL);
	if (x == NULL)
		return false;

	cc = integer_non_null(po, x);
	if (cc == CC_ERROR)
		return false;
	newobj = integer_conditional(po, cc,
				     (long) Py_True,
				     (long) Py_False);
	if (newobj == NULL)
		return false;

	/* move the resulting non-virtual Python object back into 'boolobj' */
	vinfo_move(po, boolobj, newobj);
	return true;
}

static PyObject* direct_compute_bool(vinfo_t* boolobj, char* data)
{
	PyObject* result;
	int ival;
	ival = direct_read_vinfo(vinfo_getitem(boolobj, iBOOL_OB_IVAL), data);
	if (ival == -1 && PyErr_Occurred())
		return NULL;
	result = ival ? Py_True : Py_False;
	Py_INCREF(result);
	return result;
}


DEFINEVAR source_virtual_t psyco_computed_bool;


 /***************************************************************/
  /*** boolean objects meta-implementation                     ***/

#define CONVERT_TO_BOOL(vobj, vlng)				\
	switch (Psyco_VerifyType(po, vobj, &PyBool_Type)) {	\
	case true:   /* vobj is a PyBoolObject */		\
		vlng = PsycoInt_AS_LONG(po, vobj);		\
		if (vlng == NULL)				\
			return NULL;				\
		break;						\
	case false:  /* vobj is not a PyBoolObject */		\
		return pint_base2op(po, v, w, op);		\
	default:     /* error or promotion */			\
		return NULL;					\
	}

static vinfo_t* pbool_base2op(PsycoObject* po, vinfo_t* v, vinfo_t* w,
			      vinfo_t*(*op)(PsycoObject*,vinfo_t*,vinfo_t*))
{
	vinfo_t* a;
	vinfo_t* b;
	vinfo_t* x;
	CONVERT_TO_BOOL(v, a);
	CONVERT_TO_BOOL(w, b);
	x = op (po, a, b);
	if (x != NULL)
		x = PsycoBool_FROM_LONG(x);
	return x;
}

static vinfo_t* pbool_or(PsycoObject* po, vinfo_t* v, vinfo_t* w)
{
	return pbool_base2op(po, v, w, integer_or);
}

static vinfo_t* pbool_xor(PsycoObject* po, vinfo_t* v, vinfo_t* w)
{
	return pbool_base2op(po, v, w, integer_xor);
}

static vinfo_t* pbool_and(PsycoObject* po, vinfo_t* v, vinfo_t* w)
{
	return pbool_base2op(po, v, w, integer_and);
}


INITIALIZATIONFN
void psy_boolobject_init(void)
{
	PyNumberMethods *m = PyBool_Type.tp_as_number;

	Psyco_DefineMeta(m->nb_or,       pbool_or);
	Psyco_DefineMeta(m->nb_xor,      pbool_xor);
	Psyco_DefineMeta(m->nb_and,      pbool_and);

	INIT_SVIRTUAL(psyco_computed_bool, compute_bool,
		      direct_compute_bool, 0, 0, 0);
}

#else /* !BOOLEAN_TYPE */
INITIALIZATIONFN
void psy_boolobject_init(void) { }
#endif /* BOOLEAN_TYPE */
