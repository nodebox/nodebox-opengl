 /***************************************************************/
/***           Psyco equivalent of structmember.h              ***/
 /***************************************************************/

#ifndef _PSY_STRUCTMEMBER_H
#define _PSY_STRUCTMEMBER_H

#include "../Python/pycompiler.h"
#include "pobject.h"


EXTERNFN
vinfo_t* PsycoMember_GetOne(PsycoObject* po, vinfo_t* addr, PyMemberDef* l);


#endif /* _PSY_STRUCTMEMBER_H */
