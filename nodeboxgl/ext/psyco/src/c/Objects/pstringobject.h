 /***************************************************************/
/***           Psyco equivalent of stringobject.h              ***/
 /***************************************************************/

#ifndef _PSY_STRINGOBJECT_H
#define _PSY_STRINGOBJECT_H


#include "pobject.h"
#include "pabstract.h"

#define USE_CATSTR 0  /*trying to use only bufstring virtual strings instead*/
#define USE_BUFSTR 1


/* various ways to access the actual character data */
#define STR_sval      UNSIGNED_ARRAY(char, offsetof(PyStringObject, ob_sval))
#define STR_sval2     UNSIGNED_ARRAY(short, offsetof(PyStringObject, ob_sval))
#define STR_sval4     UNSIGNED_ARRAY(long, offsetof(PyStringObject, ob_sval))


/* all flavors of virtual strings */
#define VIRTUALSTR_FIRST  FIELDS_TOTAL(FIX_size)

/* virtual one-character strings */
#define CHARACTER_CHAR    VIRTUALSTR_FIRST
#define CHARACTER_TOTAL   (CHARACTER_CHAR+1)

/* virtual string slices */
#define STRSLICE_SOURCE   VIRTUALSTR_FIRST
#define STRSLICE_START    (STRSLICE_SOURCE+1)
#define STRSLICE_TOTAL    (STRSLICE_START+1)

#if USE_CATSTR
/* virtual string concatenations */
#define CATSTR_LIST       VIRTUALSTR_FIRST
#define CATSTR_TOTAL      (CATSTR_LIST+1)
#endif

#if USE_BUFSTR
/* virtual overallocated-buffer concatenations */
#define BUFSTR_BUFOBJ     VIRTUALSTR_FIRST
#define BUFSTR_TOTAL      (BUFSTR_BUFOBJ+1)
#endif


#define PsycoString_Check(tp) PyType_TypeCheck(tp, &PyString_Type)
#ifdef Py_USING_UNICODE
# define PsycoUnicode_Check(tp) PyType_TypeCheck(tp, &PyUnicode_Type)
#else
# define PsycoUnicode_Check(tp)                 0
#endif


PSY_INLINE vinfo_t* PsycoString_AS_STRING(PsycoObject* po, vinfo_t* v)
{	/* no type check */
	return integer_add_i(po, v, offsetof(PyStringObject, ob_sval), false);
}
PSY_INLINE vinfo_t* PsycoString_GET_SIZE(PsycoObject* po, vinfo_t* v)
{	/* no type check */
	return psyco_get_const(po, v, FIX_size);
}


EXTERNFN vinfo_t* PsycoCharacter_New(vinfo_t* chrval);
EXTERNFN bool PsycoCharacter_Ord(PsycoObject* po, vinfo_t* v, vinfo_t** vord);


#endif /* _PSY_STRINGOBJECT_H */
