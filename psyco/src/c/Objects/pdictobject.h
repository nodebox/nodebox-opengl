 /***************************************************************/
/***            Psyco equivalent of dictobject.h               ***/
 /***************************************************************/

#ifndef _PSY_DICTOBJECT_H
#define _PSY_DICTOBJECT_H


#include "pobject.h"
#include "pabstract.h"


EXTERNFN vinfo_t* PsycoDict_New(PsycoObject* po);
EXTERNFN vinfo_t* PsycoDict_Copy(PsycoObject* po, vinfo_t* orig);
EXTERNFN bool PsycoDict_SetItem(PsycoObject* po, vinfo_t* vdict,
				PyObject* key, vinfo_t* vvalue);


#endif /* _PSY_LISTOBJECT_H */
