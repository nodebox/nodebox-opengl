 /***************************************************************/
/***          Structures used by the dispatcher part           ***/
 /***************************************************************/

#ifndef _DISPATCHER_H
#define _DISPATCHER_H


#include "psyco.h"
#include "vcompiler.h"
#include "processor.h"
#include "codegen.h"


/* a frozen PsycoObject is a snapshot of an actual PsycoObject,
   capturing the state of the compiler in a form that can be used
   later to compare live states to it.
   The FrozenPsycoObject's secondary goal is to capture enough
   information to rebuild a "live" PsycoObject, close enough to
   the original to let the next few Python instructions produce
   exactly the same machine code as the original. See
   psyco_prepare_respawn(). Be careful, there are a lot of such
   snapshots around in memory; keep them as small as possible.

   The first implementation (with VLOCALS_OPC=0) stores a copy
   of the PsycoObject vlocals. So does the second implementation
   (VLOCALS_OPC=1), but it compresses the copy into a very compact
   pseudo-code. */
#define VLOCALS_OPC  1

struct FrozenPsycoObject_s {
  union {
    int fz_stack_depth;
    struct respawn_s* respawning;
  } fz_stuff;
#if VLOCALS_OPC
  Source* fz_vlocals_opc;     /* compact pseudo-code copy */
#else
  vinfo_array_t* fz_vlocals;       /* verbatim copy */
#endif
  PROCESSOR_FROZENOBJECT_FIELDS
  short fz_respawned_cnt;
  CodeBufferObject* fz_respawned_from;
  pyc_data_t* fz_pyc_data;  /* only partially allocated */
};


/* construction */
PSY_INLINE void fpo_mark_new(FrozenPsycoObject* fpo) {
	fpo->fz_respawned_cnt = 0;
	fpo->fz_respawned_from = NULL;
}
PSY_INLINE void fpo_mark_unused(FrozenPsycoObject* fpo) {
#if VLOCALS_OPC
	fpo->fz_vlocals_opc = NULL;
#else
	fpo->fz_vlocals = NullArray;
#endif
	fpo->fz_pyc_data = NULL;
}
EXTERNFN void fpo_build(FrozenPsycoObject* fpo, PsycoObject* po);
EXTERNFN void fpo_release(FrozenPsycoObject* fpo);

/* build a 'live' PsycoObject from frozen snapshot */
EXTERNFN PsycoObject* fpo_unfreeze(FrozenPsycoObject* fpo);

/* inspection */
PSY_INLINE int get_stack_depth(FrozenPsycoObject* fpo) {
	return fpo->fz_stuff.fz_stack_depth;
}

/* psyco_compatible():
   search in the given global_entries_t for a match to the live PsycoObject.
   Return NULL if no match is found, or a vcompatible_t structure otherwise.
   The returned 'diff' is an array of the 'vinfo_t*' of 'po' which are
   compile-time but should be un-promoted to run-time. In particular, the
   array is empty (==NullArray) if an exact match is found.

   The current implementation is not re-entrent. The returned vcompatible_t
   structure must be released by psyco_stabilize() or one of the psyco_unify
   functions below, before another call to psyco_compatible() can be made.
*/
typedef struct {
  CodeBufferObject* matching;   /* best match */
  vinfo_array_t* diff;          /* array of differences */
} vcompatible_t;
EXTERNFN vcompatible_t* psyco_compatible(PsycoObject* po,
                                         global_entries_t* pattern);

EXTERNFN void psyco_stabilize(vcompatible_t* lastmatch);


/*****************************************************************/
 /***   "Global Entries"                                        ***/

/* global entry points for the compiler. One global entry point holds a list
   of already-compiled code buffers corresponding to the various states
   in which the compiler has already be seen at this point. See
   psyco_compatible().

   The dispatcher saves all CodeBufferObjects (with their copy of the
   compiler state) in a list for each 'entry point' of the compiler
   (the main entry point is spec_main_loop, the start of the main loop).
   When coming back to this entry point later, the list let us determine
   whether we already encountered the same state.
   
   The details of this structure are private.
   XXX implemented as a list object holding CodeBufferObjects in no
   XXX particular order. Must be optimized for reasonably fast searches
   XXX if the lists become large (more than just a few items).

   The list starts with PyIntObjects whose numbers tell which local variables
   may safely be deleted at that point.
*/
struct global_entries_s {
	PyObject* fatlist;      /* list of PyIntObjects then CodeBufferObjects */
};

/* initialize a global_entries_t structure */
PSY_INLINE void psyco_ge_init(global_entries_t* ge) {
	ge->fatlist = PyList_New(0);
	if (ge->fatlist == NULL)
		OUT_OF_MEMORY();
}

/* register the code buffer; it will be found by future calls to
   psyco_compatible(). */
PSY_INLINE int register_codebuf(global_entries_t* ge, CodeBufferObject* codebuf) {
	return PyList_Append(ge->fatlist, (PyObject*) codebuf);
}

/* for mergepoints.c */
PSY_INLINE void psyco_ge_unused_var(global_entries_t* ge, int num)
{
	PyObject* o = PyInt_FromLong(num);
	if (o == NULL || PyList_Append(ge->fatlist, o))
		OUT_OF_MEMORY();
}

EXTERNFN void psyco_delete_unused_vars(PsycoObject* po, global_entries_t* ge);


/*****************************************************************/
 /***   Unification                                             ***/

/* Update 'po' to match 'lastmatch', then jump to 'lastmatch'.
   For the conversion we might have to emit some code.
   If po->code == NULL or there is not enough room between code and
   po->codelimit, a new code buffer is created. A new reference to
   the new or target code buffer is returned in 'target'.
   If po->code != NULL, the return value points at the end of the
   code that has been written there; otherwise, the return value is
   undefined (but not NULL).
   'po' and 'lastmatch' are released.
*/
EXTERNFN code_t* psyco_unify(PsycoObject* po, vcompatible_t* lastmatch,
                             CodeBufferObject** target);

/* Simplified interface to psyco_unify() without using a previously
   existing code buffer (i.e. 'po->code' is uninitialized). If needed,
   return a new buffer with the necessary code followed by a JMP to
   'lastmatch'. If no code is needed, just return a new reference to
   'lastmatch->matching'.
*/
EXTERNFN CodeBufferObject* psyco_unify_code(PsycoObject* po,
                                            vcompatible_t* lastmatch);

/* To "simplify" recursively a vinfo_array_t. The simplification done
   is to replace run-time values inside a sub-array of a non-virtual
   value with NULL, and to remove sub-arrays of constant-time values.
   We assume that these can still be reloaded later if necessary.
   Returns the number of run-time values left.
   This assumes that all 'tmp' marks are cleared in 'array'. */
EXTERNFN int psyco_simplify_array(vinfo_array_t* array,
                                  PsycoObject* po);  /* 'po' may be NULL */

/* Emit the code to prepare for Psyco code calling Psyco code in
   a compiled function call */
PSY_INLINE bool psyco_forking(PsycoObject* po, vinfo_array_t* array) {
	/* Some virtual-time objects cannot remain virtualized across calls,
	   because if the called function pulls them out of virtual-time,
	   the caller will not know it.  This is unacceptable for
	   mutable Python objects.  We hope it does not hurt in other cases,
	   but could be defeated by the "is" operator. */
	return psyco_limit_nested_weight(po, array, NWI_FUNCALL,
                                         NESTED_WEIGHT_END);
}

/*****************************************************************/
 /***   Promotion                                               ***/

/* Promotion of a run-time variable into a fixed compile-time one.
   Finish the code block with a jump to the dispatcher that
   promotes the run-time variable 'fix' to compile-time. This
   usually means the compiler will be called back again, at the
   given entry point.
   Note: Releases 'po'.
*/
EXTERNFN code_t* psyco_finish_promotion(PsycoObject* po, vinfo_t* fix,
                                        int pflags);

#if USE_RUNTIME_SWITCHES
/* Promotion of certain run-time values into compile-time ones
   (promotion only occurs for values inside a given set, e.g. for
   types that we know how to optimize). The special values are
   described in an array of long, turned into a source_known_t
   (see processor.h).
   Note: Releases 'po'.
*/
EXTERNFN code_t* psyco_finish_fixed_switch(PsycoObject* po, vinfo_t* fix,
                                           long kflags,
                                           fixed_switch_t* special_values);
#endif

/* Un-Promotion from non-fixed compile-time into run-time.
   Note: this does not release 'po'. Un-promoting is easy and
   don't require encoding calls to the dispatcher.
*/
EXTERNFN void psyco_unfix(PsycoObject* po, vinfo_t* vi);


/*****************************************************************/
 /***   Respawning                                              ***/

/* internal use */
EXTERNFN void* psyco_prepare_respawn_ex(PsycoObject* po,
                                        condition_code_t jmpcondition,
                                        void* fn, int extrasize);
EXTERNFN bool psyco_prepare_respawn(PsycoObject* po,
                                    condition_code_t jmpcondition);
EXTERNFN code_t* psyco_do_respawn(void* arg, int extrasize);
EXTERNFN code_t* psyco_dont_respawn(void* arg, int extrasize);
EXTERNFN void psyco_respawn_detected(PsycoObject* po);
#define detect_respawn_ex(po)  (!++(po)->respawn_cnt)
PSY_INLINE bool detect_respawn(PsycoObject* po) {
	if (detect_respawn_ex(po)) {
		psyco_respawn_detected(po);
		return true;
	}
	else
		return false;
}
PSY_INLINE bool is_respawning(PsycoObject* po) { return po->respawn_cnt < 0; }

/* the following powerful function stands for 'if the processor flag (cond) is
   set at run-time, then...'. Of course we do not know yet if this will be
   the case or not, but the macro takes care of preparing the required
   respawns if needed. 'cond' may be CC_ALWAYS_xxx or a real processor flag.
   runtime_condition_f() assumes the outcome is generally false,
   runtime_condition_t() assumes the outcome is generally true. */
PSY_INLINE bool runtime_condition_f(PsycoObject* po, condition_code_t cond) {
	extra_assert(cond != CC_ERROR);
	if (cond == CC_ALWAYS_FALSE) return false;
	if (cond == CC_ALWAYS_TRUE) return true;
        return psyco_prepare_respawn(po, cond);
}
PSY_INLINE bool runtime_condition_t(PsycoObject* po, condition_code_t cond) {
	extra_assert(cond != CC_ERROR);
	if (cond == CC_ALWAYS_TRUE) return true;
	if (cond == CC_ALWAYS_FALSE) return false;
        return !psyco_prepare_respawn(po, INVERT_CC(cond));
}
/* extreme care is needed when using the runtime_condition_x() functions:
   they must *always* get called in a sequence that doesn't depend on external
   factors that may change. If a call is in one branch on an if/else, for
   example, then you must make sure that the "if" condition cannot give a
   different result during later respawning. See load_global for a what to do
   if this is not the case. */

/* the following functions let you test at compile-time the fact that a
   value is 0 or not. Returns 0 or 1, or -1 in case of error.
   Uses integer_NON_NULL() and so accepts 'vi==NULL' and !!consumes a ref!!
   *Do not use* for values that might hold a reference to a PyObject;
   use object_non_null() in this case. */
EXTERNFN int runtime_NON_NULL_f(PsycoObject* po, vinfo_t* vi);
EXTERNFN int runtime_NON_NULL_t(PsycoObject* po, vinfo_t* vi);

/* check if an integer is between the given *inclusive* bounds.
   Same return values as above.  Does not consume a ref. */
EXTERNFN int runtime_in_bounds(PsycoObject* po, vinfo_t* vi,
                               long lowbound, long highbound);


#endif /* _DISPATCHER_H */
