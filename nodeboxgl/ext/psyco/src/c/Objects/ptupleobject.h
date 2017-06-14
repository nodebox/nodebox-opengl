 /***************************************************************/
/***            Psyco equivalent of tupleobject.h              ***/
 /***************************************************************/

#ifndef _PSY_TUPLEOBJECT_H
#define _PSY_TUPLEOBJECT_H


#include "pobject.h"
#include "pabstract.h"


#define TUPLE_ob_item   FARRAY(DEF_FIELD(PyTupleObject, PyObject*, ob_item, \
						FIX_size))
#define iTUPLE_OB_ITEM  FIELD_INDEX(TUPLE_ob_item)

/* The following macro reads an item from a Psyco tuple without any
   checks. Be sure the item has already been loaded in the array of
   the vinfo_t. This should only be used after a successful call to
   PsycoTuple_Load(). */
#define PsycoTuple_GET_ITEM(vtuple, index)  \
		((vtuple)->array->items[iTUPLE_OB_ITEM + (index)])


/***************************************************************/
/* virtual tuples.
   If 'source' is not NULL it gives the content of the tuple.
   If 'source' is NULL you have to initialize it yourself. */
EXTERNFN vinfo_t* PsycoTuple_New(int count, vinfo_t** source);

/* get the (possibly virtual) array of items in the tuple,
   returning the length of the tuple or -1 if it fails (items not known).
   The items are then found in PsycoTuple_GET_ITEM(tuple, i).
   Never sets a PycException. */
EXTERNFN int PsycoTuple_Load(vinfo_t* tuple);

EXTERNFN vinfo_t* PsycoTuple_Concat(PsycoObject* po, vinfo_t* v1, vinfo_t* v2);


#endif /* _PSY_TUPLEOBJECT_H */
