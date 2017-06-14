 /***************************************************************/
/***               Detection of Python features                ***/
 /***************************************************************/

#ifndef _PYVER_H
#define _PYVER_H


#include <Python.h>

#define PSYCO_VERSION_HEX          0x010502f0   /* 1.5.2 */


/*****************************************************************/
 /***   Detects differences between Python versions             ***/

/* Note: not all features can be automatically detected; in some cases
   we just assume that the feature is present or not based on some
   other feature that has been introduced roughly at the same time.
   This may need fixes to compile with some intermediary Python
   versions. */

#define PSYCO_CAN_CALL_UNICODE     0   /* prevent references to PyUnicode_Xxx
                                          functions causing potential linker
                                          errors because of UCS2/UCS4 name
                                          mangling */

#define HAVE_arrayobject_allocated (PY_VERSION_HEX>=0x02040000)   /* 2.4 */
#define VERYCONVOLUTED_IMPORT_NAME (PY_VERSION_HEX>=0x02050000)   /* 2.5 */

#if HAVE_LONG_LONG && !defined(PY_LONG_LONG)
# define PY_LONG_LONG   LONG_LONG   /* Python < 2.3 */
#endif

#ifdef PyBool_Check
# define BOOLEAN_TYPE              1    /* Python >=2.3 */
#else
# define BOOLEAN_TYPE              0
#endif

#ifndef PyString_CHECK_INTERNED
# define PyString_CHECK_INTERNED(op) (((PyStringObject*)(op))->ob_sinterned)
#endif

#ifndef PyMODINIT_FUNC
# define PyMODINIT_FUNC void
#endif

#ifndef PyExceptionClass_Check    /* Python < 2.5 */
# define PyExceptionClass_Check(x)	PyClass_Check(x)
# define PyExceptionInstance_Check(x)	PyInstance_Check(x)
# define PyExceptionInstance_Class(x)	\
				(PyObject*)((PyInstanceObject*)(x))->in_class
#endif

#ifdef Py_TPFLAGS_HAVE_INDEX  /* Python >= 2.5 */
# define HAVE_NB_INDEX		1
# define PsycoIndex_Check(tp)						\
		((tp)->tp_as_number != NULL &&				\
		 PyType_HasFeature((tp), Py_TPFLAGS_HAVE_INDEX) &&	\
		 (tp)->tp_as_number->nb_index != NULL)

#else
# define HAVE_NB_INDEX		0
#endif

/* for extra fun points, let's try to emulate Python's ever-changing behavior
   (but not too hard; you can still tell the difference in Python < 2.5 if
   you use -sys.maxint-1 as the lower bound of a slice, provided you inspect
   it with a custom __getslice__() */
#if PY_VERSION_HEX < 0x02030000
#  define LARGE_NEG_LONG_AS_SLICE_INDEX		0		/* 2.2 */
#elif PY_VERSION_HEX < 0x02050000
#  define LARGE_NEG_LONG_AS_SLICE_INDEX		(-INT_MAX)	/* 2.3, 2.4 */
#else
#  define LARGE_NEG_LONG_AS_SLICE_INDEX		(-INT_MAX-1)	/* 2.5 */
#endif

#define HAVE_NEGATIVE_IDS   (PY_VERSION_HEX < 0x02050000)   /* Python < 2.5 */

#endif /* _PYVER_H */
