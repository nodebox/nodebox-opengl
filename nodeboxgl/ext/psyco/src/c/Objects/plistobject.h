 /***************************************************************/
/***            Psyco equivalent of listobject.h               ***/
 /***************************************************************/

#ifndef _PSY_LISTOBJECT_H
#define _PSY_LISTOBJECT_H


#include "pobject.h"
#include "pabstract.h"


#define LIST_ob_item       FMUT(DEF_FIELD(PyListObject, PyObject**, ob_item, \
                                          VAR_size))
#define LIST_TOTAL         FIELDS_TOTAL(LIST_ob_item)
#define VLIST_ITEMS        LIST_TOTAL
#define LIST_itemsarray    FMUT(DEF_ARRAY(PyObject*, 0))


/* Warning: only for very short lists! Each new length could
   force a new copy of the whole code to be emitted... */
#define VLIST_LENGTH_MAX   3


EXTERNFN vinfo_t* PsycoList_New(PsycoObject* po, int size, vinfo_t** source);
EXTERNFN vinfo_t* PsycoList_SingletonNew(vinfo_t* vitem);
EXTERNFN bool PsycoList_Append(PsycoObject* po, vinfo_t* v, vinfo_t* vitem);
/*EXTERNVAR vinfo_t* psyco_empty_list;*/

/* get the virtual array of items in the list,
   returning the length of the list or -1 if it fails (items not known).
   The items are then found in list->array->items[VLIST+i].
   Never sets a PycException. */
EXTERNFN int PsycoList_Load(vinfo_t* list);


/* for pstringobject.c */
EXTERNFN vinfo_t* psyco_plist_concat(PsycoObject* po, vinfo_t* a, vinfo_t* b);

/* for piterobject.c */
EXTERNFN vinfo_t* plist_item(PsycoObject* po, vinfo_t* a, vinfo_t* i);


#endif /* _PSY_LISTOBJECT_H */
