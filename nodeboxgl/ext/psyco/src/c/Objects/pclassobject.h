 /***************************************************************/
/***            Psyco equivalent of classobject.h              ***/
 /***************************************************************/

#ifndef _PSY_CLASSOBJECT_H
#define _PSY_CLASSOBJECT_H


#include "pobject.h"
#include "pabstract.h"


/* Instance methods */
#define METHOD_im_func   DEF_FIELD(PyMethodObject, PyObject*, im_func,  OB_type)
#define METHOD_im_self   DEF_FIELD(PyMethodObject, PyObject*, im_self,  \
						METHOD_im_func)
#define METHOD_im_class  DEF_FIELD(PyMethodObject, PyObject*, im_class, \
						METHOD_im_self)
#define iMETHOD_IM_FUNC  FIELD_INDEX(METHOD_im_func)
#define iMETHOD_IM_SELF  FIELD_INDEX(METHOD_im_self)
#define iMETHOD_IM_CLASS FIELD_INDEX(METHOD_im_class)
#define METHOD_TOTAL     FIELDS_TOTAL(METHOD_im_class)


EXTERNFN vinfo_t* pinstancemethod_call(PsycoObject* po, vinfo_t* methobj,
                                       vinfo_t* arg, vinfo_t* kw);


 /***************************************************************/
  /***   Virtual-time object builder                           ***/

/* not-yet-computed instance method objects. Usually not computed at all,
   but if it needs be, will call PyMethod_New(). */
EXTERNVAR source_virtual_t psyco_computed_method;

EXTERNFN
vinfo_t* PsycoMethod_New(PyObject* func, vinfo_t* self, PyObject* cls);


#endif /* _PSY_CLASSOBJECT_H */
