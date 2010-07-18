 /***************************************************************/
/***            Psyco equivalent of funcobject.h               ***/
 /***************************************************************/

#ifndef _PSY_FUNCOBJECT_H
#define _PSY_FUNCOBJECT_H


#include "pobject.h"
#include "pabstract.h"


#define FUNC_code      DEF_FIELD(PyFunctionObject, PyObject*, func_code, OB_type)
#define FUNC_globals   DEF_FIELD(PyFunctionObject, PyObject*, func_globals,  \
						FUNC_code)
#define FUNC_defaults  DEF_FIELD(PyFunctionObject, PyObject*, func_defaults, \
						FUNC_globals)
#define iFUNC_CODE     FIELD_INDEX(FUNC_code)
#define iFUNC_GLOBALS  FIELD_INDEX(FUNC_globals)
#define iFUNC_DEFAULTS FIELD_INDEX(FUNC_defaults)
#define FUNC_TOTAL     FIELDS_TOTAL(FUNC_defaults)


EXTERNFN vinfo_t* pfunction_call(PsycoObject* po, vinfo_t* func,
                                 vinfo_t* arg, vinfo_t* kw);
EXTERNFN vinfo_t* pfunction_simple_call(PsycoObject* po, PyObject* f,
					vinfo_t* arg, bool allow_inline);


/***************************************************************/
/* virtual functions.                                          */
/* 'fdefaults' may be NULL.                                    */
EXTERNFN vinfo_t* PsycoFunction_New(PsycoObject* po, vinfo_t* fcode,
                                    vinfo_t* fglobals, vinfo_t* fdefaults);


#endif /* _PSY_FUNCOBJECT_H */
