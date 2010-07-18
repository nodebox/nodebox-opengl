 /***************************************************************/
/***                Tables of code merge points                ***/
 /***************************************************************/

#ifndef _MERGEPOINTS_H
#define _MERGEPOINTS_H


#include "psyco.h"
#include "dispatcher.h"
#include <compile.h>

/* A merge point is a point reached by two or more control paths in
   the bytecode. They are a subset of the targets found by the standard
   module function dis.findlabels(). It may be a subset because some
   targets can only be reached by jumping from a single point, e.g. 'else:'.
   Such targets are not merge points.
*/

struct mergepoint_s {
  int bytecode_position;
  global_entries_t entries;
};

/* 'bytecode_ptr' gives the position of the merge point in the bytecode.
   An array of mergepoint_t structures is sorted against this field.

   'entries' is a list of snapshots of the compiler states previously
   encountered at this point.
*/

/* Caching version of the following function */
EXTERNFN PyObject* psyco_get_merge_points(PyCodeObject* co, int module);

/* The following function detects the merge points and builds an array of
   mergepoint_t structures, stored into a Python string object. It returns
   Py_None if the bytecode uses unsupported instructions. */
EXTERNFN PyObject* psyco_build_merge_points(PyCodeObject* co, int module);

/* Get a pointer to the first mergepoint_t structure in the array whose
   'bytecode_ptr' is >= position. */
EXTERNFN mergepoint_t* psyco_next_merge_point(PyObject* mergepoints,
					      int position);

/* Get a pointer to the very first mergepoint_t structure in the array */
PSY_INLINE mergepoint_t* psyco_first_merge_point(PyObject* mergepoints)
{
  extra_assert(PyString_Check(mergepoints));
  return (mergepoint_t*) PyString_AS_STRING(mergepoints);
}

/* Same as psyco_next_merge_point() but returns NULL if bytecode_ptr!=position */
PSY_INLINE mergepoint_t* psyco_exact_merge_point(PyObject* mergepoints,
                                             int position)
{
  mergepoint_t* mp = psyco_next_merge_point(mergepoints, position);
  if (mp->bytecode_position != position)
    mp = NULL;
  return mp;
}


#define MP_FLAGS_HAS_EXCEPT      1   /* the code block has an 'except' clause */
#define MP_FLAGS_HAS_FINALLY     2   /* the code block has a 'finally' clause */
#define MP_FLAGS_INLINABLE       4   /* function could be inlined             */
#define MP_FLAGS_MODULE          8   /* can only run as module top-level code */
#define MP_FLAGS_CONTROLFLOW    16   /* can use early deletion of locals      */
#define MP_FLAGS_EXTRA       (-256)

PSY_INLINE int psyco_mp_flags(PyObject* mergepoints)
{
  char* endptr = PyString_AS_STRING(mergepoints)+PyString_GET_SIZE(mergepoints);
  return ((int*) endptr)[-1];
}

/* end of PsycoObject construction */
PSY_INLINE mergepoint_t* PsycoObject_Ready(PsycoObject* po) {
	mergepoint_t* mp;
	psyco_assert_coherent(po);
	mp = psyco_first_merge_point(po->pr.merge_points);
	psyco_delete_unused_vars(po, &mp->entries);
        return mp;
}

/* A user-defined filter function to prevent compilation of some code objs */
EXTERNVAR PyObject* psyco_codeobj_filter_fn;


#endif /* _MERGEPOINTS_H */
