 /***************************************************************/
/***             Psyco equivalent of object.h                  ***/
 /***************************************************************/

#ifndef _PSY_OBJECT_H
#define _PSY_OBJECT_H


#include "../Python/pycompiler.h"


/*#define OB_REFCOUNT         never directly manipulated*/
#define OB_type      DEF_FIELD(PyObject, PyTypeObject*, ob_type, NO_PREV_FIELD)
#define FIX_size     NONNEG_FIELD(PyVarObject,     int, ob_size, OB_type)
#define VAR_size     FMUT(FIX_size)
#define FIX_signed_size DEF_FIELD(PyVarObject,     int, ob_size, OB_type)
#define VAR_signed_size FMUT(FIX_signed_size)

#define iOB_TYPE   FIELD_INDEX(OB_type)
#define iFIX_SIZE  FIELD_INDEX(FIX_size)
#define iVAR_SIZE  FIELD_INDEX(VAR_size)


/* common type checkers, rewritten because in Psyco we manipulate type
   objects directly and Python's usual macros insist on taking a regular
   PyObject* whose type is checked. */
# define PyType_TypeCheck(tp1, tp)  	\
	((tp1) == (tp) || PyType_IsSubtype((tp1), (tp)))

#define PsycoIter_Check(tp) \
    (PyType_HasFeature(tp, Py_TPFLAGS_HAVE_ITER) && \
     (tp)->tp_iternext != NULL)

#define PsycoSequence_Check(tp) \
	((tp)->tp_as_sequence && (tp)->tp_as_sequence->sq_item != NULL)


/* Return the type of an object, or NULL in case of exception (typically
   a promotion exception). */
EXTERNFN PyTypeObject* Psyco_NeedType(PsycoObject* po, vinfo_t* vi);

PSY_INLINE PyTypeObject* Psyco_FastType(vinfo_t* vi) {
	/* fast version.  Only call this when you know the type has
	   already been loaded by a previous Psyco_NeedType() */
	vinfo_t* vtp = vinfo_getitem(vi, iOB_TYPE);
	if (vtp == NULL) {
		PyObject* o = (PyObject*) CompileTime_Get(vi->source)->value;
		return o->ob_type;
	}
	else {
		return (PyTypeObject*) CompileTime_Get(vtp->source)->value;
	}
}
#if USE_RUNTIME_SWITCHES
# error "Disabled because of type inheritance. The switch overlooks subtypes."
/* Check for the type of an object. Returns the index in the set 'fs' or
   -1 if not in the set (or if exception). Used this is better than
   Psyco_NeedType() if you are only interested in some types, not all of them. */
PSY_INLINE int Psyco_TypeSwitch(PsycoObject* po, vinfo_t* vi, fixed_switch_t* fs) {
	vinfo_t* vtp = get_array_item(po, vi, OB_TYPE);
	if (vtp == NULL)
		return -1;
	return psyco_switch_index(po, vtp, fs);
}
#endif

/* Is the given object is of the given type (or a subtype of it) ?
   Returns -1 in case of error or if promotion is requested. */
PSY_INLINE int Psyco_VerifyType(PsycoObject* po, vinfo_t* vi, PyTypeObject* tp) {
	PyTypeObject* vtp = Psyco_NeedType(po, vi);
	if (vtp == NULL)
		return -1;
	return PyType_TypeCheck(vtp, tp);
}
/* Return the type that the object is known to be of, or NULL if unknown.
   Never fails. */
EXTERNFN PyTypeObject* Psyco_KnownType(vinfo_t* vi);

/* Use this to assert the type of an object. Do not use unless you are
   sure about it! (e.g. don't use this for integer-computing functions
   if they might return a long in case of overflow) */
PSY_INLINE void Psyco_AssertType(PsycoObject* po, vinfo_t* vi, PyTypeObject* tp) {
	psyco_assert_field(po, vi, OB_type, (long) tp);
}

/* Same as integer_non_null() but assumes we are testing a PyObject* pointer,
   so that only compile-time NULLs or run-time pointers from which we have
   not read anything yet can be NULL. Virtual-time pointers are assumed never
   to be NULL. */
PSY_INLINE condition_code_t object_non_null(PsycoObject* po, vinfo_t* v) {
	if (is_virtualtime(v->source) || v->array != NullArray)
		return CC_ALWAYS_TRUE;
	else
		return integer_non_null(po, v);
}


/* The following functions are Psyco implementations of common functions
   of the standard interpreter. */
EXTERNFN vinfo_t* PsycoObject_IsTrue(PsycoObject* po, vinfo_t* vi);
EXTERNFN vinfo_t* PsycoObject_Repr(PsycoObject* po, vinfo_t* vi);

/* Note: DelAttr() is SetAttr() with 'v' set to NULL (and not some vinfo_t
   that would happend to contain zero). */
EXTERNFN vinfo_t* PsycoObject_GetAttr(PsycoObject* po, vinfo_t* o,
                                      vinfo_t* attr_name);
EXTERNFN bool PsycoObject_SetAttr(PsycoObject* po, vinfo_t* o,
                                  vinfo_t* attr_name, vinfo_t* v);
EXTERNFN vinfo_t* PsycoObject_GenericGetAttr(PsycoObject* po, vinfo_t* obj,
                                             vinfo_t* vname);

EXTERNFN vinfo_t* PsycoObject_RichCompare(PsycoObject* po, vinfo_t* v,
					  vinfo_t* w, int op);
EXTERNFN vinfo_t* PsycoObject_RichCompareBool(PsycoObject* po,
                                              vinfo_t* v,
                                              vinfo_t* w, int op);


/* a quick way to specify the type of the object returned by an operation
   when it is known, without having to go into all the details of the
   operation itself (be careful, you must be *sure* of the return type): */

#define DEF_KNOWN_RET_TYPE_1(cname, op, flags, knowntype)	\
    DEF_KNOWN_RET_TYPE_internal(cname, knowntype,		\
				(PsycoObject* po, vinfo_t* v1),	\
				(po, op, flags, "v", v1))
#define DEF_KNOWN_RET_TYPE_2(cname, op, flags, knowntype)			\
    DEF_KNOWN_RET_TYPE_internal(cname, knowntype,				\
				(PsycoObject* po, vinfo_t* v1, vinfo_t* v2),	\
				(po, op, flags, "vv", v1, v2))
#define DEF_KNOWN_RET_TYPE_3(cname, op, flags, knowntype)			\
    DEF_KNOWN_RET_TYPE_internal(cname, knowntype,				\
				(PsycoObject* po, vinfo_t* v1, vinfo_t* v2,	\
					vinfo_t* v3),				\
				(po, op, flags, "vvv", v1, v2, v3))
#define DEF_KNOWN_RET_TYPE_4(cname, op, flags, knowntype)			\
    DEF_KNOWN_RET_TYPE_internal(cname, knowntype,				\
				(PsycoObject* po, vinfo_t* v1, vinfo_t* v2,	\
					vinfo_t* v3, vinfo_t* v4),		\
				(po, op, flags, "vvvv", v1, v2, v3, v4))

#define DEF_KNOWN_RET_TYPE_internal(cname, knowntype, fargs, gargs)	\
static vinfo_t* cname  fargs  {						\
	vinfo_t* result = psyco_generic_call  gargs ;			\
	if (result != NULL && !IS_NOTIMPLEMENTED(result)) {		\
		Psyco_AssertType(po, result, knowntype);		\
	}								\
	return result;							\
}

/* 'true' unless 'x' is exactly the special 'not implemented' value
   built by psyco_generic_call with CfPyErrNotImplemented */
#define IS_IMPLEMENTED(x)	((x) == NULL || !IS_NOTIMPLEMENTED(x))

/* is 'x' the special 'not implemented' value? */
#define IS_NOTIMPLEMENTED(x)	\
	((x)->source == CompileTime_NewSk(&psyco_skNotImplemented))


#if USE_RUNTIME_SWITCHES
/* definition of commonly used "fixed switches", i.e. sets of
   values (duplicating fixed switch structures for the same set
   of value can inccur a run-time performance loss in some cases) */

/* the variable names list the values in order.
   'int' means '&PyInt_Type' etc. */
EXTERNVAR fixed_switch_t psyfs_int;
EXTERNVAR fixed_switch_t psyfs_int_long;
EXTERNVAR fixed_switch_t psyfs_int_long_float;
EXTERNVAR fixed_switch_t psyfs_tuple_list;
EXTERNVAR fixed_switch_t psyfs_string_unicode;
EXTERNVAR fixed_switch_t psyfs_tuple;
EXTERNVAR fixed_switch_t psyfs_dict;
EXTERNVAR fixed_switch_t psyfs_none;
/* NOTE: don't forget to update pobject.c when adding new variables here */
#endif

/* for dispatcher.c */
EXTERNFN vinfo_t* Psyco_SafelyDeleteVar(PsycoObject* po, vinfo_t* vi);


#endif /* _PSY_OBJECT_H */
