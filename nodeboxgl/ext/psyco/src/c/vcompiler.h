 /***************************************************************/
/***           Structures used by the compiler part            ***/
 /***************************************************************/

#ifndef _VCOMPILER_H
#define _VCOMPILER_H

#include "psyco.h"
#include <iencoding.h>
#include "blockalloc.h"
#include "Python/pycheader.h"


/*****************************************************************/
 /***   Definition of the "sources" of vinfo_t structures       ***/


/* A "source" defines the stage of the variable (run-time,
   compile-time or virtual-time), and gives information about
   the value of the variable */
typedef long Source;   /* Implemented as a bitfield 32-bit integer. */

/* the next typedefs are for documentation purposes only, as the C compiler
   will not make any difference between them all */
typedef long RunTimeSource;
typedef long CompileTimeSource;
typedef long VirtualTimeSource;

#define RunTime         0
#define CompileTime     1    /* a.k.a. "Known value" */
#define VirtualTime     2
#define TimeMask        (CompileTime | VirtualTime)

PSY_INLINE bool is_runtime(Source s)     { return (s & TimeMask) == RunTime; }
PSY_INLINE bool is_compiletime(Source s) { return (s & CompileTime) != 0; }
PSY_INLINE bool is_virtualtime(Source s) { return (s & VirtualTime) != 0; }
PSY_INLINE long gettime(Source s)        { return s & TimeMask; }
#define CHKTIME(src, time)           extra_assert(gettime(src) == (time))


/************************ Run-time sources *******************************
 *
 * If the last two bits of 'source' are 'RunTime', we have a run-time value.
 * The rest of 'source' encodes both the position of the value in the stack
 * (or StackNone) and the register holding this value (or REG_NONE).
 *
 **/

#if REG_TOTAL > 8
# error "fix the masks below"
#endif

/* flags */
#define RunTime_StackMask    0x01FFFFFC
#define RunTime_StackMax     RunTime_StackMask
#define RunTime_StackNone    0
#define RunTime_RegMask      0xF0000000
#define RunTime_NoRef        0x08000000
#define RunTime_NonNeg       0x04000000
#define RunTime_Megamorphic  0x02000000
#define RunTime_FlagsMask    RunTime_NoRef

/* construction */
PSY_INLINE RunTimeSource RunTime_New1(int stack_position,
#if REG_TOTAL > 0
				  reg_t reg,
#endif
				  bool ref, bool nonneg)
{
	long result = RunTime + stack_position;
#if REG_TOTAL > 0
	result += (long) reg << 28;
#endif
	if (!ref)
		result += RunTime_NoRef;
	if (nonneg)
		result += RunTime_NonNeg;
	return (RunTimeSource) result;
}
#if REG_TOTAL > 0
# define RunTime_NewStack(stackpos, ref, nonneg)		\
            RunTime_New1(stackpos, REG_NONE, ref, nonneg)
# define RunTime_New(reg, ref, nonneg)				\
            RunTime_New1(RunTime_StackNone, reg, ref, nonneg)
#else
# define RunTime_NewStack  RunTime_New1
#endif

/* field inspection */
PSY_INLINE bool has_rtref(Source s) {
	return (s & (TimeMask|RunTime_NoRef)) == RunTime;
}
#if REG_TOTAL > 0
PSY_INLINE reg_t getreg(RunTimeSource s)     { CHKTIME(s, RunTime); return (reg_t)(s >> 28); }
#endif
PSY_INLINE bool is_reg_none(RunTimeSource s) { CHKTIME(s, RunTime); return s < 0; }
PSY_INLINE int getstack(RunTimeSource s)     { CHKTIME(s, RunTime); return s & RunTime_StackMask; }
PSY_INLINE bool is_runtime_with_reg(Source s) {
  return (s & (TimeMask|(1<<31))) == 0;
}
PSY_INLINE bool is_rtnonneg(RunTimeSource s) { CHKTIME(s, RunTime); return s & RunTime_NonNeg; }


/* mutation */
PSY_INLINE RunTimeSource remove_rtref(RunTimeSource s) { CHKTIME(s, RunTime); return s | RunTime_NoRef; }
PSY_INLINE RunTimeSource add_rtref(RunTimeSource s)    { CHKTIME(s, RunTime); return s & ~RunTime_NoRef; }
#if REG_TOTAL > 0
PSY_INLINE RunTimeSource set_rtreg_to(RunTimeSource s, reg_t newreg) {
	CHKTIME(s, RunTime);
	return (s & ~RunTime_RegMask) | ((long) newreg << 28);
}
PSY_INLINE RunTimeSource set_rtreg_to_none(RunTimeSource s) {
	CHKTIME(s, RunTime);
	return s | ((long) REG_NONE << 28);
}
#endif
PSY_INLINE RunTimeSource set_rtstack_to(RunTimeSource s, int stack) {
	CHKTIME(s, RunTime);
	extra_assert(getstack(s) == RunTime_StackNone);
	return s | stack;
}
PSY_INLINE RunTimeSource set_rtstack_to_none(RunTimeSource s) {
	CHKTIME(s, RunTime);
	return s & ~RunTime_StackMask;
}
PSY_INLINE RunTimeSource set_rtnonneg(RunTimeSource s) {
	CHKTIME(s, RunTime);
	return s | RunTime_NonNeg;
}


/************************ Compile-time sources *******************************
 *
 * if the last two bits of 'source' are 'CompileTime',
 * the rest of 'source' points to a 'source_known_t' structure:
 *
 **/
typedef struct {
	long refcount1_flags; /* flags and reference counter */
	long value;           /* compile-time known value */
} source_known_t;

/* flags for source_known_t::refcount1_flags: */

/* flag added when producing code that relies
   essentially on this value to be constant */
#define SkFlagFixed   0x01

/* value is a PyObject* and holds a reference */
#define SkFlagPyObj   0x02

/* first unused flag */
#define SkFlagEnd     0x04
#define SkFlagMask    (SkFlagEnd-1)

/* refcounting */
EXTERNFN void sk_release(source_known_t *sk);
PSY_INLINE void sk_incref(source_known_t *sk) { sk->refcount1_flags += SkFlagEnd; }
PSY_INLINE void sk_decref(source_known_t *sk) {
	if ((sk->refcount1_flags -= SkFlagEnd)<0) sk_release(sk);
}

/* construction */
BLOCKALLOC_INTERFACE(sk, source_known_t)

PSY_INLINE source_known_t* sk_new(long v, long flags) {
	source_known_t* sk = psyco_llalloc_sk();
	sk->refcount1_flags = flags;
	sk->value = v;
	return sk;
}
PSY_INLINE void sk_delete(source_known_t* sk) {
	psyco_llfree_sk(sk);
}


/* Compile-time sources */
/* construction */
PSY_INLINE CompileTimeSource CompileTime_NewSk(source_known_t* newsource) {
	extra_assert((((long) newsource) & TimeMask) == 0);
	return (CompileTimeSource) (((char*) newsource) + CompileTime);
}
PSY_INLINE CompileTimeSource CompileTime_New(long value) {
	return CompileTime_NewSk(sk_new(value, 0));
}

/* inspection */
PSY_INLINE source_known_t* CompileTime_Get(CompileTimeSource s) {
	CHKTIME(s, CompileTime);
	return (source_known_t*)(((char*) s) - CompileTime);
}
PSY_INLINE CompileTimeSource set_ct_value(CompileTimeSource s, long v) {
	source_known_t* sk = CompileTime_Get(s);
        extra_assert((sk->refcount1_flags & SkFlagPyObj) == 0);
	if (sk->refcount1_flags < SkFlagEnd) {
		sk->value = v; /* reuse object when only one reference */
		return s;
	}
	else {
		sk_decref(sk);
		return CompileTime_NewSk(sk_new(v, sk->refcount1_flags &
						SkFlagMask));
	}
}


/************************ Virtual-time sources *******************************
 *
 * if the last two bits of 'source' are VIRTUAL_TIME,
 * the rest of 'source' points to a 'source_virtual_t' structure (in psyco.h).
 * Description of the fields of source_virtual_t:
 *
 *  compute_fn_t compute_fn;
 *     the function to be called to move the vinfo_t out of virtual-time.
 *
 *  direct_compute_fn_t direct_compute_fn
 *     a non-meta function that computes the PyObject* out of raw data.
 *     'compute_fn' is the meta version of 'direct_compute_fn'.
 *
 *  long pyobject_mask
 *     a bitfield, one bit per item in the vinfo_t's array: the bit is set
 *     to 1 if the array item represents a PyObject (and hence needs to be
 *     forced to have a reference if the virtual object escapes the current
 *     scope, which so far is only possible through compactobject attrs).
 *
 *  signed char nested_weight[2];
 *     a value > 0 prevents infinite nesting of virtual 'vinfo_t's inside
 *     of other virtual 'vinfo_t's: the sum of all 'nested_weight' fields
 *     of a chain of nested 'vinfo_t's should always be less than
 *     NESTED_WEIGHT_END. There are two values because limiting some kind
 *     of virtual 'vinfo_t's is more important across function calls than
 *     inside the same function.
 **/
#define NESTED_WEIGHT_END   15
#define NWI_NORMAL          0  /* use nested_weight[0] */
#define NWI_FUNCALL         1  /* use nested_weight[1] */
#define INIT_SVIRTUAL(sv, fn, directfn, objmask, w_normal, w_funcall) do { \
	(sv).compute_fn = fn;                                              \
	(sv).direct_compute_fn = directfn;                                 \
	(sv).pyobject_mask = objmask;                                      \
	(sv).nested_weight[NWI_NORMAL] = w_normal;                         \
	(sv).nested_weight[NWI_FUNCALL] = w_funcall;                       \
} while (0)
#define INIT_SVIRTUAL_NOCALL(sv, fn, w_normal)                             \
		INIT_SVIRTUAL(sv, fn, NULL, 0, w_normal, NW_FORCE)
#define SVIRTUAL_MUTABLE(sv)	((sv)->nested_weight[NWI_FUNCALL] == NW_FORCE)

/* some weights for common virtual-time objects, grouped here to better
   show their relative importance. A careful tuning is required to avoid
   code size explosion. (The following figures are only a guess; some
   real-code testing would be welcome.) */
#define NW_VLISTS               5
#define NW_TUPLES_NORMAL        4
#define NW_TUPLES_FUNCALL       4
#define NW_STRSLICES_NORMAL     5
#define NW_STRSLICES_FUNCALL    9
#define NW_CATSTRS_NORMAL       4  /* catstrs also have a vlist internally */
#define NW_CATSTRS_FUNCALL      7
#define NW_BUFSTRS_NORMAL       5
#define NW_FORCE                NESTED_WEIGHT_END  /* always force */

/* construction */
PSY_INLINE VirtualTimeSource VirtualTime_New(source_virtual_t* sv) {
	extra_assert((((long) sv) & TimeMask) == 0);
	return (VirtualTimeSource) (((char*) sv) + VirtualTime);
}

/* inspection */
PSY_INLINE source_virtual_t* VirtualTime_Get(VirtualTimeSource s) {
	CHKTIME(s, VirtualTime);
	return (source_virtual_t*)(((char*) s) - VirtualTime);
}


EXTERNVAR source_virtual_t psyco_vsource_not_important;

#define SOURCE_NOT_IMPORTANT    VirtualTime_New(&psyco_vsource_not_important)
#define SOURCE_DUMMY            RunTime_NewStack(RunTime_StackNone, false, false)
#define SOURCE_DUMMY_WITH_REF   RunTime_NewStack(RunTime_StackNone, true, false)
#define SOURCE_ERROR            ((Source) -1)



 /***************************************************************/
/***      Definition of the fundamental vinfo_t structure      ***/
 /***************************************************************/


/* 'array' fields are never NULL, but point to a fraction of vinfo_array_t
 * in which 'count' is 0, like 'NullArray'.
 * This allows 'array->count' to always return a sensible value.
 * Invariant: the array is dynamically allocated if and only if 'array->count'
 * is greater than 0.
 */
EXTERNVAR const long psyco_zero;
#define NullArrayAt(zero_variable)  ((vinfo_array_t*)(&(zero_variable)))
#define NullArray                   NullArrayAt(psyco_zero)


struct vinfo_array_s {
	int count;
	vinfo_t* items[7];  /* always variable-sized */
};

/* construction */
EXTERNFN vinfo_array_t* array_grow1(vinfo_array_t* array, int ncount);
PSY_INLINE void array_release(vinfo_array_t* array) {
	if (array->count > 0) PyMem_FREE(array);
}
PSY_INLINE vinfo_array_t* array_new(int ncount) {
	if (ncount > 0)
		return array_grow1(NullArray, ncount);
	else
		return NullArray;
}


/* 'vinfo_t' defines for the compiler the stage of a
   variable and where it is found. It is a wrapper around a 'Source'.
   For pointers to structures, 'array' is used to decompose the structure
   fields into 'vinfo_t'-described variables which can in turn
   be at various stages. */
struct vinfo_s {
	int refcount;           /* reference counter */
	Source source;
	vinfo_array_t* array;   /* substructure variables or a NullArray */
	vinfo_t* tmp;           /* internal use of the dispatcher */
};

/* construction */
BLOCKALLOC_INTERFACE(vinfo, vinfo_t)

PSY_INLINE vinfo_t* vinfo_new(Source src) {
	vinfo_t* vi = psyco_llalloc_vinfo();
	vi->refcount = 1;
	vi->source = src;
	vi->array = NullArray;
	return vi;
}
PSY_INLINE vinfo_t* vinfo_new_skref(Source src) {
	if (is_compiletime(src)) sk_incref(CompileTime_Get(src));
	return vinfo_new(src);
}

/* copy constructor */
EXTERNFN vinfo_t* vinfo_copy(vinfo_t* vi);

/* refcounting */
#define VINFO_CHECKREF						\
	extra_assert(vi->refcount >= 1);			\
	extra_assert(vi->refcount < 0x1000000 /* arbitrary */);
EXTERNFN void vinfo_release(vinfo_t* vi, PsycoObject* po);
PSY_INLINE void vinfo_incref(vinfo_t* vi) { VINFO_CHECKREF ++vi->refcount; }
PSY_INLINE void vinfo_decref(vinfo_t* vi, PsycoObject* po) {
	VINFO_CHECKREF
	if (!--vi->refcount) vinfo_release(vi, po);
}
PSY_INLINE void vinfo_xdecref(vinfo_t* vi, PsycoObject* po) {
	if (vi != NULL) vinfo_decref(vi, po);
}

/* promoting out of virtual-time */
PSY_INLINE bool compute_vinfo(vinfo_t* vi, PsycoObject* po) {
	if (is_virtualtime(vi->source)) {
		if (!VirtualTime_Get(vi->source)->compute_fn(po, vi))
			return false;
		extra_assert(!is_virtualtime(vi->source));
	}
	return true;
}
EXTERNFN bool psyco_limit_nested_weight(PsycoObject* po, vinfo_array_t* array,
					int nw_index, signed char nw_end);
EXTERNFN long direct_read_vinfo(vinfo_t* vi, char* data);
EXTERNFN PyObject* direct_xobj_vinfo(vinfo_t* vi, char* data);

PSY_INLINE bool vinfo_known_equal(vinfo_t* v, vinfo_t* w) {
	return (v->source == w->source &&
		(v == w || !is_virtualtime(v->source)));
}

/* misc */
PSY_INLINE bool is_nonneg(Source s) {
	switch (gettime(s)) {
	case RunTime:     return is_rtnonneg(s);
	case CompileTime: return CompileTime_Get(s)->value >= 0;
	default:          return false;
	}
}
PSY_INLINE void assert_nonneg(vinfo_t* v) {
	if (is_runtime(v->source))
		v->source = set_rtnonneg(v->source);
	else
		extra_assert(is_virtualtime(v->source) || is_nonneg(v->source));
}

/* sub-array (see also psyco_get_field()&co.) */
PSY_INLINE void vinfo_array_grow(vinfo_t* vi, int ncount) {
	if (ncount > vi->array->count)
		vi->array = array_grow1(vi->array, ncount);
}
EXTERNFN void vinfo_array_shrink(PsycoObject* po, vinfo_t* vi, int ncount);
PSY_INLINE vinfo_t* vinfo_getitem(vinfo_t* vi, int index) {
	if (((unsigned int) index) < ((unsigned int) vi->array->count))
		return vi->array->items[index];
	else
		return NULL;
}
PSY_INLINE vinfo_t* vinfo_needitem(vinfo_t* vi, int index) {
	vinfo_array_grow(vi, index+1);
	return vi->array->items[index];
}
PSY_INLINE void vinfo_setitem(PsycoObject* po, vinfo_t* vi, int index,
                          vinfo_t* newitem) {
	/* consumes a reference to 'newitem' */
	if (newitem != NULL) {
		extra_assert(!(is_compiletime(vi->source) &&
			       !is_compiletime(newitem->source)));
	}
	vinfo_array_grow(vi, index+1);
	vinfo_xdecref(vi->array->items[index], po);
	vi->array->items[index] = newitem;
}


/* array management */
EXTERNFN void clear_tmp_marks(vinfo_array_t* array);
#if ALL_CHECKS
EXTERNFN void assert_cleared_tmp_marks(vinfo_array_t* array);
EXTERNFN void assert_array_contains_nonct(vinfo_array_t* array, vinfo_t* vi);
#else
PSY_INLINE void assert_cleared_tmp_marks(vinfo_array_t* array) { }   /* nothing */
PSY_INLINE void assert_array_contains_nonct(vinfo_array_t* a, vinfo_t* v) { }
#endif
EXTERNFN void duplicate_array(vinfo_array_t* target, vinfo_array_t* source);
PSY_INLINE void deallocate_array(vinfo_array_t* array, PsycoObject* po) {
	int i = array->count;
	while (i--) vinfo_xdecref(array->items[i], po);
}
PSY_INLINE void array_delete(vinfo_array_t* array, PsycoObject* po) {
	deallocate_array(array, po);
	array_release(array);
}


/*****************************************************************/
 /***   read and write fields of structures in memory           ***/

/* Implementation of defield_t as a single packed bitfield,
   stored as a pointer to enable type checks in the C compiler */
/* [This is internal stuff: see comments below for an introduction.] */
/* type is defined by its size (given as the nth power of two)
   and a handful of flags */
typedef struct undefined_fld_s* defield_t;
EXTERNFN vinfo_t* psyco_internal_getfld(PsycoObject* po, int findex,
					defield_t df, vinfo_t* vi, long offset);
EXTERNFN bool psyco_internal_putfld(PsycoObject* po, int findex, defield_t df,
				    vinfo_t* vi, long offset, vinfo_t* value);
#define FIELD_INDEX_MASK  0x00FF
#define FIELD_MUTABLE     0x0100
#define FIELD_ARRAY       0x0200
#define FIELD_UNSIGNED    0x0400
#define FIELD_NONNEG      0x0800
#define FIELD_PYOBJ_REF   0x1000
#define FIELD_SIZE2_SHIFT 13
#define FIELD_INTL_NOREF  0x8000
#define FIELD_OFS_SHIFT   16
#define NO_PREV_FIELD     ((defield_t) -1)
#define FIELD_RESERVED_INDEX  0xCC
#define SIZE2_FROM_CTYPE(ctype) \
	(sizeof(ctype)==1 ? 0 : \
	 sizeof(ctype)==2 ? 1 : \
	 sizeof(ctype)==4 ? 2 : \
	 sizeof(ctype)==8 ? 3 : \
	 (extra_assert(!"field size is not a small power of two"), 0))
/*#define FIELD_NTH(df, n)
	(extra_assert(FIELD_INDEX(df)+(n) == FIELD_INDEX((df)+(n))),
	((df) + (n) + (((n) << FIELD_SIZE2(df)) << FIELD_OFS_SHIFT))*/
#define STRUCT_FIELD_BUILD(cstruct, ctype, cfield, prevf, flags)	\
	((defield_t) ((offsetof(cstruct, cfield) << FIELD_OFS_SHIFT) |	\
		      (SIZE2_FROM_CTYPE(ctype) << FIELD_SIZE2_SHIFT) |	\
		      field_next_index(prevf, true) |			\
		      flags))
#define ARRAY_FIELD_BUILD(ctype, baseofs, flags)			\
	((defield_t) (((baseofs) << FIELD_OFS_SHIFT) | 			\
		      (SIZE2_FROM_CTYPE(ctype) << FIELD_SIZE2_SHIFT) | 	\
		      FIELD_RESERVED_INDEX | FIELD_ARRAY |		\
		      flags))


/*****************************************************************
 * You must describe the fields of each C structure of the interpreter
 * that you want Psyco to work with.  Use the following macros field
 * by field.  Each macro returns a defield_t which contains the
 * definition of the field. */

/* build the field definition corresponding to:
    - the C structure whose name is in 'cstruct';
    - the C type given by 'ctype';
    - the field name given by 'cfield'.
   For the field order you must give in 'prevf' the defield_t
   corresponding to the previous field of the C structure,
   or NO_PREV_FIELD if you are defining the first field. */
#define DEF_FIELD(cstruct, ctype, cfield, prevf) \
	STRUCT_FIELD_BUILD(cstruct, ctype, cfield, prevf, 0)

/* special case: use the following macro instead of DEF_FIELD
   if 'ctype' is an unsigned numeric type. */
#define UNSIGNED_FIELD(cstruct, ctype, cfield, prevf) \
	STRUCT_FIELD_BUILD(cstruct, ctype, cfield, prevf, FIELD_UNSIGNED)

/* signed fields that are known to be non-negative */
#define NONNEG_FIELD(cstruct, ctype, cfield, prevf) \
	STRUCT_FIELD_BUILD(cstruct, ctype, cfield, prevf, FIELD_NONNEG)

/* the same, for pure arrays instead of structures */
#define DEF_ARRAY(ctype, baseofs) \
	ARRAY_FIELD_BUILD(ctype, baseofs, 0)
#define UNSIGNED_ARRAY(ctype, baseofs) \
	ARRAY_FIELD_BUILD(ctype, baseofs, FIELD_UNSIGNED)

/* you can surround DEF_FIELD() by FARRAY(), FMUT(), FPYREF():
    - FARRAY() means that the field is actually an array in the
      structure, as for example 'ob_items' in PyTupleObject;
    - FMUT() means that the field is mutable;
    - FPYREF() means that we want to read or store a PyObject* reference */
#define FARRAY(df)  ((defield_t) ((long)(df) | FIELD_ARRAY))
#define FMUT(df)    ((defield_t) ((long)(df) | FIELD_MUTABLE))
#define FPYREF(df)  (extra_assert(1<<FIELD_SIZE2(df) == sizeof(PyObject*)), \
                     (defield_t) ((long)(df) | FIELD_PYOBJ_REF))

/* inspection of a defield_t:
    - FIELDS_TOTAL(df) returns the number of fields of the structure
      defined so far, if 'df' is the defield_t of the last field;
    - FIELD_INDEX(df) returns the 0-based index of 'df' in vinfo->array;
    - 1<<FIELD_SIZE2(df) computes the size of the field 'df';
    - FIELD_C_OFFSET(df) is the offset of 'df' in the C structure. */
#define FIELDS_TOTAL(lastdf)  (field_next_index(lastdf, false))
#define FIELD_INDEX(df)    ((long)(df) & FIELD_INDEX_MASK)
#define FIELD_SIZE2(df)   (((long)(df) >> FIELD_SIZE2_SHIFT) & 3)
#define FIELD_C_OFFSET(df)   ((long)(df) >> FIELD_OFS_SHIFT)
#define FIELD_HAS_REF(df)  ((long)(df) & FIELD_PYOBJ_REF)
#define CHECK_FIELD_INDEX(n)  extra_assert((unsigned)FIELD_INDEX(n) <	\
					   FIELD_RESERVED_INDEX)

/* functions to read or write a field from or to the structure 
   pointed to by 'vi': */
PSY_INLINE vinfo_t* psyco_get_field(PsycoObject* po, vinfo_t* vi, defield_t df) {
	return psyco_internal_getfld(po, FIELD_INDEX(df), df,
				     vi, FIELD_C_OFFSET(df));
}
PSY_INLINE vinfo_t* psyco_get_nth_field(PsycoObject* po, vinfo_t* vi, defield_t df,
				    int index) {
	long ofs = index << FIELD_SIZE2(df);
	return psyco_internal_getfld(po, FIELD_INDEX(df) + index, df,
				     vi, FIELD_C_OFFSET(df) + ofs);
}
PSY_INLINE vinfo_t* psyco_get_field_offset(PsycoObject* po, vinfo_t* vi,
				       defield_t df, long offset) {
	extra_assert((long)df & FIELD_MUTABLE);
	return psyco_internal_getfld(po, FIELD_RESERVED_INDEX, df,
				     vi, FIELD_C_OFFSET(df) + offset);
}
EXTERNFN vinfo_t* psyco_get_field_array(PsycoObject* po, vinfo_t* vi,
					defield_t df, vinfo_t* vindex);
PSY_INLINE bool psyco_put_field(PsycoObject* po, vinfo_t* vi, defield_t df,
			    vinfo_t* value) {
	return psyco_internal_putfld(po, FIELD_INDEX(df), df,
				     vi, FIELD_C_OFFSET(df), value);
}
PSY_INLINE bool psyco_put_nth_field(PsycoObject* po, vinfo_t* vi, defield_t df, 
				int index, vinfo_t* value) {
	long ofs = index << FIELD_SIZE2(df);
	return psyco_internal_putfld(po, FIELD_INDEX(df) + index, df,
				     vi, FIELD_C_OFFSET(df) + ofs, value);
}
EXTERNFN bool psyco_put_field_array(PsycoObject* po, vinfo_t* vi, defield_t df,
                                    vinfo_t* vindex, vinfo_t* value);

/* fields of size 8 (like those of type 'double') are accessed as two
   vinfo_t's, for the second of which we use the following macro */
#define FIELD_PART2(df)  ((defield_t) ((long)(df) + 1 +     /* next index */  \
			    (sizeof(long)<<FIELD_OFS_SHIFT))) /* next ofs */

/* these special-case convenient functions do not return a new
   vinfo_t* reference that you have to worry about and eventually release;
   but they only work for immutable fields. */
PSY_INLINE vinfo_t* psyco_get_const(PsycoObject* po, vinfo_t* vi, defield_t df) {
	return psyco_internal_getfld(po, FIELD_INDEX(df),
                                     (defield_t) ((long)df | FIELD_INTL_NOREF),
				     vi, FIELD_C_OFFSET(df));
}
PSY_INLINE vinfo_t* psyco_get_nth_const(PsycoObject* po, vinfo_t* vi, defield_t df,
				    int index) {
	long ofs = index << FIELD_SIZE2(df);
	return psyco_internal_getfld(po, FIELD_INDEX(df) + index,
                                     (defield_t) ((long)df | FIELD_INTL_NOREF),
				     vi, FIELD_C_OFFSET(df) + ofs);
}

/* "forgets" the saved value for the field 'df' in 'vi'.  Used when an
   immutable field changes after all, or when a virtual-time structure that
   stores mutable fields is computed (because the mutable fields can actually
   be mutated by anyone after the structure is computed). */
PSY_INLINE void psyco_forget_field(PsycoObject* po, vinfo_t* vi, defield_t df) {
	CHECK_FIELD_INDEX(df);
	vinfo_setitem(po, vi, FIELD_INDEX(df), NULL);
}
PSY_INLINE void psyco_forget_nth_field(PsycoObject* po, vinfo_t* vi, defield_t df,
				   int index) {
	CHECK_FIELD_INDEX(df);
	vinfo_setitem(po, vi, FIELD_INDEX(df) + index, NULL);
}

/* to tell Psyco you are sure you know the value of a given field */
EXTERNFN void psyco_assert_field(PsycoObject* po, vinfo_t* vi, defield_t df,
                                 long value);


/* internal */
#if PSYCO_DEBUG
/* in debugging mode, use the function;  while optimizing, we favour
   the macro version below because GCC does not completely optimize out
   recursive calls to functions with completely constant arguments. */
PSY_INLINE int field_next_index(defield_t df, bool ovf) {
	if (df == NO_PREV_FIELD)
		return 0;
	else {
		int n = FIELD_INDEX(df);
		int field_size = 1 << FIELD_SIZE2(df);
		CHECK_FIELD_INDEX(df);
		/* arrays are variable-sized */
		extra_assert(!((long)df & FIELD_ARRAY));
		/* round up */
		n += (field_size + sizeof(long)-1) / sizeof(long);
		if (ovf)  /* check for index overflow */
			extra_assert(n == FIELD_INDEX(n));
		return n;
	}
}
#else
/*  this macro seriously slows down compilation because it expands 'df'
    three times, producing exponential explosion in the preprocessor --
    still, the result is generally a constant. */
#  define field_next_index(df, ovf)    ((df) == NO_PREV_FIELD ? 0 :		\
     FIELD_INDEX(df) + ((1 << FIELD_SIZE2(df)) + sizeof(long)-1) / sizeof(long))
#endif


/*****************************************************************/
 /***   PsycoObject: state of the compiler                      ***/


struct PsycoObject_s {
  /* used to be a Python object, hence the name */

  /* assembly code */
  code_t* code;                /* where the emitted code goes                */
  code_t* codelimit;           /* do not write code past this limit          */

  /* compiler private variables for producing and optimizing code */
  PROCESSOR_PSYCOOBJECT_FIELDS      /* processor state                       */
  int respawn_cnt;                  /* see psyco_prepare_respawn()           */
  CodeBufferObject* respawn_proxy;  /* see psyco_prepare_respawn()           */
  pyc_data_t pr;                    /* private language-dependent data       */

  /* finally, the description of variable stages. This is the data against
     which state matches and synchronizations are performed. */
  vinfo_array_t vlocals;          /* all the 'vinfo_t' variables             */
  /* variable-sized array! */
};

#define PSYCOOBJECT_SIZE(arraycnt)                                      \
	(sizeof(PsycoObject)-sizeof(vinfo_array_t) + sizeof(int) +      \
         (arraycnt)*sizeof(vinfo_t*))

/* move 'vsource->source' into 'vtarget->source'. Must be the last reference
   to 'vsource', which is freed. 'vsource' must have no array, and
   'vtarget->source' must hold no reference to anything. In short, this
   function must not be used except by virtual-time computers. */
EXTERNFN void vinfo_move(PsycoObject* po, vinfo_t* vtarget, vinfo_t* vsource);


/*****************************************************************/
 /***   Compiler language-independent functions                 ***/

/* compilation */

/* Main compiling function. Emit machine code corresponding to the state
   'po'. The compiler produces its code into 'code' and the return value is
   the end of the written code. 'po' is freed. 'mp' is the current mergepoint
   position or NULL if there is no mergepoint here.

   Be sure to call clear_tmp_marks(&po->vlocals) before this function.

   'continue_compilation' is normally false. When compile() is called
   during the compilation of 'po', 'continue_compilation' is true and
   psyco_compile() may return NULL to tell the caller to continue the
   compilation of 'po' itself. The sole purpose of this is to reduce the
   depth of recursion of the C stack.
*/
EXTERNFN code_t* psyco_compile(PsycoObject* po, mergepoint_t* mp,
                               bool continue_compilation);

/* Conditional compilation: the state 'po' is compiled to be executed only if
   'condition' holds. In general this creates a coding pause for it to be
   compiled later. It always makes a copy of 'po' so that the original can be
   used to compile the other case ('not condition'). 'condition' must not be
   CC_ALWAYS_xxx here. 'mp' is the current mergepoint position or NULL if there
   is no mergepoint here.
*/
EXTERNFN void psyco_compile_cond(PsycoObject* po, mergepoint_t* mp,
                                 condition_code_t condition);

/* Simplified interface to compile() without using a previously
   existing code buffer. Return a new code buffer. */
EXTERNFN CodeBufferObject* psyco_compile_code(PsycoObject* po, mergepoint_t* mp);

/* Prepare a 'coding pause', i.e. a short amount of code (proxy) that will be
   called only if the execution actually reaches it to go on with compilation.
   'po' is the PsycoObject corresponding to the proxy.
   'condition' may not be CC_ALWAYS_FALSE.
   The (possibly conditional) jump to the proxy is encoded in 'calling_code'.
   When the execution reaches the proxy, 'resume_fn' is called and the proxy
   destroys itself and replaces the original jump to it by a jump to the newly
   compiled code. */
typedef code_t* (*resume_fn_t)(PsycoObject* po, void* extra);
EXTERNFN void psyco_coding_pause(PsycoObject* po, condition_code_t jmpcondition,
				 resume_fn_t resume_fn,
				 void* extra, int extrasize);

/* management functions; see comments in compiler.c */
#if ALL_CHECKS
EXTERNFN void psyco_assert_coherent1(PsycoObject* po, bool full);
#else
#  define psyco_assert_coherent1(po, full)  do { } while (0) /* nothing */
#endif
#define psyco_assert_coherent(po)    psyco_assert_coherent1(po, true)

/* construction */
PSY_INLINE PsycoObject* PsycoObject_New(int vlocalscnt) {
	int psize = PSYCOOBJECT_SIZE(vlocalscnt);
	PsycoObject* po = (PsycoObject*) PyMem_MALLOC(psize);
	if (po == NULL)
		OUT_OF_MEMORY();
	memset(po, 0, psize);
	return po;
}
EXTERNFN PsycoObject* psyco_duplicate(PsycoObject* po);  /* internal */
PSY_INLINE PsycoObject* PsycoObject_Duplicate(PsycoObject* po) {
	clear_tmp_marks(&po->vlocals);
	return psyco_duplicate(po);
}
EXTERNFN void PsycoObject_Delete(PsycoObject* po);
PSY_INLINE PsycoObject* PsycoObject_Resize(PsycoObject* po, int nvlocalscnt) {
	int psize = PSYCOOBJECT_SIZE(nvlocalscnt);
	return (PsycoObject*) PyMem_REALLOC(po, psize);
}


#endif /* _VCOMPILER_H */
