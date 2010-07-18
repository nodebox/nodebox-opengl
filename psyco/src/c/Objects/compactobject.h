 /***************************************************************/
/*** A "regular" PyObject type with Psyco-optimized attributes ***/
 /***************************************************************/

#ifndef _COMPACTOBJECT_H
#define _COMPACTOBJECT_H


#include "../psyco.h"
#include "../Python/pyver.h"
#include "../vcompiler.h"


typedef struct compact_impl_s compact_impl_t;  /* private structure */

typedef struct {
	PyObject_HEAD
	char*           k_data;  /* heap-allocated memory for the attributes */
	compact_impl_t* k_impl;  /* description of how the data is encoded */
} PyCompactObject;


EXTERNVAR PyTypeObject PyCompact_Type;
EXTERNVAR compact_impl_t* PyCompact_EmptyImpl;

#define PyCompact_Check(op)	PyObject_TypeCheck(op, &PyCompact_Type)


/* EXTERNFN PyObject* PyCompact_New(void); */
/* EXTERNFN PyObject* PyCompact_GetSlot(PyObject* ko, PyObject* key); */
/* EXTERNFN PyObject* PyCompact_SetSlot(PyObject* ko, PyObject* key, */
/*                                      PyObject* value); */
/* EXTERNFN int PyCompact_Extend(PyObject* ko, compact_impl_t* nimpl); */
/* EXTERNFN compact_impl_t* PyCompact_ExtendImpl(compact_impl_t* oldimpl, */
/*                                               PyObject* attr, */
/*                                               vinfo_t* v_descr); */

/*****************************************************************/
/* Private structures and routines exported for pcompactobject.c */

struct compact_impl_s {
	PyObject* attrname;          /* name of the last attr */
	vinfo_t* vattr;              /* storage format of the last attr */
	int datasize;                /* total size of the k_data buffer */
	compact_impl_t* extensions;  /* chained list of extensions */
	compact_impl_t* next;        /* next in chained list */
	compact_impl_t* parent;      /* of which this one is an extension */
};

#define K_ROUNDUP(sz)    (((sz) + 7) & ~7)

#define K_INTERN(attr)   do {							\
	PyString_InternInPlace(&attr);						\
	if (attr->ob_type != &PyString_Type || !PyString_CHECK_INTERNED(attr))	\
		Py_FatalError("Psyco failed to intern an attribute name");	\
} while (0)

EXTERNFN vinfo_t* vinfo_copy_no_share(vinfo_t* vi);
EXTERNFN bool k_match_vinfo(vinfo_t* vnew, vinfo_t* vexisting);
EXTERNFN compact_impl_t* k_extend_impl(compact_impl_t* oldimpl, PyObject* attr,
                                       vinfo_t* v);
EXTERNFN void k_attribute_range(vinfo_t* v, int* smin, int* smax);
EXTERNFN compact_impl_t* k_duplicate_impl(compact_impl_t* base,
                                          compact_impl_t* first_excluded,
                                          compact_impl_t* last,
                                          int shift_delta);

#endif /* _COMPACTOBJECT_H */
