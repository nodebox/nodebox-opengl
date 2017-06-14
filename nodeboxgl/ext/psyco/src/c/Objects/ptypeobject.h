 /***************************************************************/
/***            Psyco equivalent of typeobject.h               ***/
 /***************************************************************/

#ifndef _PSY_TYPEOBJECT_H
#define _PSY_TYPEOBJECT_H


#include "pobject.h"
#include "pabstract.h"


EXTERNFN vinfo_t* psyco_pobject_new(PsycoObject* po, PyTypeObject* type,
                                    vinfo_t* varg, vinfo_t* vkw);


#endif /* _PSY_TYPEOBJECT_H */
