 /***************************************************************/
/***             Psyco equivalent of boolobject.h              ***/
 /***************************************************************/

#ifndef _PSY_BOOLOBJECT_H
#define _PSY_BOOLOBJECT_H


#include "pobject.h"
#include "pabstract.h"

#if BOOLEAN_TYPE    /* Booleans were introduced in Python 2.3 */


#define BOOL_ob_ival    DEF_FIELD(PyBoolObject, long, ob_ival, OB_type)
#define iBOOL_OB_IVAL   FIELD_INDEX(BOOL_ob_ival)
#define BOOL_TOTAL      FIELDS_TOTAL(BOOL_ob_ival)


#define PsycoBool_Check(tp) PyType_TypeCheck(tp, &PyBool_Type)


 /***************************************************************/
  /***   Virtual-time object builder                           ***/

/* not-yet-computed booleans */
EXTERNVAR source_virtual_t psyco_computed_bool;

/* !! consumes a reference to vlong. PsycoBool_FromLong() does not. */
PSY_INLINE vinfo_t* PsycoBool_FROM_LONG(vinfo_t* vlong)
{
	vinfo_t* result = vinfo_new(VirtualTime_New(&psyco_computed_bool));
	result->array = array_new(BOOL_TOTAL);
	result->array->items[iOB_TYPE] =
		vinfo_new(CompileTime_New((long)(&PyBool_Type)));
	result->array->items[iBOOL_OB_IVAL] = vlong;  assert_nonneg(vlong);
	return result;
}
PSY_INLINE vinfo_t* PsycoBool_FromLong(vinfo_t* vlong)
{
	vinfo_incref(vlong);
	return PsycoBool_FROM_LONG(vlong);
}


#else /* !BOOLEAN_TYPE */
/* define the booleans as synonims for integers */
# define PsycoBool_FROM_LONG(v)  PsycoInt_FROM_LONG(v)
# define PsycoBool_FromLong(v)   PsycoInt_FromLong(v)
#endif /* BOOLEAN_TYPE */

/* utility */
#define PsycoBool_FromCondition(po, cc)                         \
	PsycoBool_FROM_LONG(psyco_vinfo_condition(po, cc))

#endif /* _PSY_INTOBJECT_H */
