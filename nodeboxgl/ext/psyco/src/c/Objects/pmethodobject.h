 /***************************************************************/
/***           Psyco equivalent of methodobject.h              ***/
 /***************************************************************/

#ifndef _PSY_METHODOBJECT_H
#define _PSY_METHODOBJECT_H


#include "pobject.h"
#include "pabstract.h"


#define CFUNC_m_ml    DEF_FIELD(PyCFunctionObject, PyMethodDef*, m_ml, OB_type)
#define CFUNC_m_self  DEF_FIELD(PyCFunctionObject, PyObject*, m_self, CFUNC_m_ml)
#define iCFUNC_M_ML   FIELD_INDEX(CFUNC_m_ml)
#define iCFUNC_M_SELF FIELD_INDEX(CFUNC_m_self)
#define CFUNC_TOTAL   FIELDS_TOTAL(CFUNC_m_self)


EXTERNFN vinfo_t* PsycoCFunction_Call(PsycoObject* po, vinfo_t* func,
                                      vinfo_t* tuple, vinfo_t* kw);


 /***************************************************************/
  /***   Virtual-time object builder                           ***/

/* not-yet-computed C method objects, with a m_ml and m_self field.
   Usually not computed at all, but if it needs be, will call
   PyCFunction_New(). */
EXTERNVAR source_virtual_t psyco_computed_cfunction;

PSY_INLINE vinfo_t* PsycoCFunction_New(PsycoObject* po, PyMethodDef* ml,
                                   vinfo_t* self)
{
	vinfo_t* result = vinfo_new(VirtualTime_New(&psyco_computed_cfunction));
	result->array = array_new(CFUNC_TOTAL);
	result->array->items[iOB_TYPE] =
		vinfo_new(CompileTime_New((long)(&PyCFunction_Type)));
	result->array->items[iCFUNC_M_ML] =
		vinfo_new(CompileTime_New((long) ml));
	vinfo_incref(self);
	result->array->items[iCFUNC_M_SELF] = self;
	return result;
}


#endif /* _PSY_METHODOBJECT_H */
