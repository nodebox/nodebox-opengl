 /***************************************************************/
/***            Psyco equivalent of longobject.h               ***/
 /***************************************************************/

#ifndef _PSY_LONGOBJECT_H
#define _PSY_LONGOBJECT_H


#include "pobject.h"
#include "pabstract.h"


#define PsycoLong_Check(tp) PyType_TypeCheck(tp, &PyLong_Type)


EXTERNFN vinfo_t* PsycoLong_AsLong(PsycoObject* po, vinfo_t* v);
EXTERNFN bool PsycoLong_AsDouble(PsycoObject* po, vinfo_t* v, vinfo_t** vd1, vinfo_t** vd2);

#endif /* _PSY_LONGOBJECT_H */
