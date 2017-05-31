 /***************************************************************/
/***     Statistics management and usage about code objects    ***/
 /***************************************************************/

#ifndef _STATS_H
#define _STATS_H

/* NB.: the real-time profilers are in profile.c */

#include "psyco.h"
#include "cstruct.h"
#include "mergepoints.h"
#include "timing.h"
#include "Python/frames.h"
#include <compile.h>
#include <frameobject.h>


#if VERBOSE_STATS
# define stats_printf(args)   debug_printf(1, args)
#else
# define stats_printf(args)   do { } while (0) /* nothing */
#endif


/* extra data attached to code objects */
typedef struct {
  PyCStruct_HEAD             /* cs_key is the code object */
  float st_charge;           /* usage statistics */
  PyObject* st_mergepoints;
  PyObject* st_codebuf;      /* as compiled from PsycoCode_CompileCode() */
  PyObject* st_globals;      /* globals used in st_codebuf */
} PyCodeStats;


/* return the PyCodeStats for 'co' */
EXTERNFN PyCodeStats* PyCodeStats_Get(PyCodeObject* co);
EXTERNFN PyCodeStats* PyCodeStats_MaybeGet(PyCodeObject* co);

/* compute and return a Borrowed reference to st_mergepoints */
PSY_INLINE PyObject* PyCodeStats_MergePoints(PyCodeStats* cs, int module) {
	PyObject* mp = cs->st_mergepoints;
	if (mp == NULL) {
		mp = psyco_build_merge_points((PyCodeObject*) cs->cs_key,
					      module);
		cs->st_mergepoints = mp;
	}
	else if (!module && mp != Py_None &&
		 (psyco_mp_flags(mp) & MP_FLAGS_MODULE))
		mp = Py_None;  /* can only run as top-level module code */
	return mp;
}


EXTERNFN void psyco_stats_reset(void);
EXTERNFN void psyco_stats_append(PyThreadState* tstate, PyFrameObject* f);
EXTERNFN void psyco_stats_collect(void);
EXTERNFN PyObject* psyco_stats_top(int n);
 /* set tunable parameters */
EXTERNFN bool psyco_stats_write(PyObject* args, PyObject* kwds);
EXTERNFN PyObject* psyco_stats_read(char* name);
EXTERNFN PyObject* psyco_stats_dump(void);


/* private timing data, based on timing.h */
#if MEASURE_ALL_THREADS
#  define measuring_state(ts)   1
#else
#  define measuring_state(ts)   ((ts) == psyco_main_threadstate)
EXTERNVAR PyThreadState* psyco_main_threadstate;
#endif


#endif /* _STATS_H */
