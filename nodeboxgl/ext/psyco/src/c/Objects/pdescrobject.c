#include "../psyfunc.h"
#include "pdescrobject.h"
#include "pstructmember.h"
#include "pmethodobject.h"


static vinfo_t* pmember_get(PsycoObject* po, PyMemberDescrObject* descr,
			    vinfo_t* obj, PyTypeObject *type)
{
	/* a meta-implementation for member_get() of descrobject.c.
	   Note that not all parameters are 'vinfo_t*'; only 'obj'
	   is. This is because PsycoObject_GenericGetAttr() gives
	   immediate values for the other two arguments. */

	/* XXX We assume that 'obj' is a valid instance of 'type'. */
	return PsycoMember_GetOne(po, obj, descr->d_member);
}

static vinfo_t* pmethod_get(PsycoObject* po, PyMethodDescrObject* descr,
			    vinfo_t* obj, PyTypeObject *type)
{
	/* a meta-implementation for method_get() of descrobject.c.
	   Same remarks as for pmember_get(). */
	return PsycoCFunction_New(po, descr->d_method, obj);
}


INITIALIZATIONFN
void psy_descrobject_init(void)
{
	PyObject* dummy;
	PyTypeObject* PyMemberDescr_Type;
	PyTypeObject* PyMethodDescr_Type;
	PyMemberDef dummydef;
        PyMethodDef dummydef2;

	/* Member descriptors */
	/* any better way to get a pointer to PyMemberDescr_Type? */
	memset(&dummydef, 0, sizeof(dummydef));
	dummydef.name = "dummy";
	dummy = PyDescr_NewMember(&PsycoFunction_Type, &dummydef);
	PyMemberDescr_Type = dummy->ob_type;
	Py_DECREF(dummy);

	Psyco_DefineMeta(PyMemberDescr_Type->tp_descr_get,
			 pmember_get);

	/* C Method descriptors */
	/* any better way to get a pointer to PyMethodDescr_Type? */
	memset(&dummydef2, 0, sizeof(dummydef2));
	dummydef2.ml_name = "dummy";
	dummy = PyDescr_NewMethod(&PsycoFunction_Type, &dummydef2);
	PyMethodDescr_Type = dummy->ob_type;
	Py_DECREF(dummy);

	Psyco_DefineMeta(PyMethodDescr_Type->tp_descr_get,
			 pmethod_get);
}
