 /***************************************************************/
/***  Turning general-purpose C structures into Python objects ***/
 /***************************************************************/

#ifndef _CSTRUCT_H
#define _CSTRUCT_H


#include "psyco.h"


#define PyCStruct_HEAD                          \
  PyObject_HEAD                                 \
  destructor cs_destructor;                     \
  PyObject* cs_key;

typedef struct {  /* internal */
  PyCStruct_HEAD
} cstruct_header_t;


EXTERNVAR PyTypeObject PyCStruct_Type;

#define PyCStruct_Check(op)	PyObject_TypeCheck(op, &PyCStruct_Type)

EXTERNFN PyObject* PyCStruct_New(size_t size, destructor d);
#define PyCStruct_NEW(TYPE, d)                          \
  ((TYPE*) PyCStruct_New(sizeof(TYPE), (destructor)(d)))

/* lookup in the given dict for the item whose key is a CStruct with
   the given key as cs_key */
PSY_INLINE PyObject* PyCStruct_DictGet(PyObject* dict, PyObject* key)
{
  cstruct_header_t sample;
  sample.ob_type = &PyCStruct_Type;
  sample.ob_refcnt = 1;
  sample.cs_key = key;
  return PyDict_GetItem(dict, (PyObject*) &sample);
}


#endif /* _CSTRUCT_H */
