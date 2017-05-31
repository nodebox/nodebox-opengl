 /***************************************************************/
/***             Profilers to collect statistics               ***/
 /***************************************************************/

#ifndef _PROFILE_H
#define _PROFILE_H


#include "psyco.h"
#include "Python/frames.h"
#include <compile.h>
#include <frameobject.h>


/* enable profiling, see comments in profile.c for the various methods */
EXTERNFN bool psyco_set_profiler(void (*rs)(void*, int));
/* where 'rs' may be: */
EXTERNFN void psyco_rs_profile(void*, int);
EXTERNFN void psyco_rs_fullcompile(void*, int);
EXTERNFN void psyco_rs_nocompile(void*, int);

/* enable the same profiling feature on all threads */
EXTERNFN void psyco_profile_threads(int start);

/* call this when it is detected to be worthwhile to give a frame a
   little Psyco help */
EXTERNFN bool psyco_turbo_frame(PyFrameObject* frame);

/* call this to mark the code object as being worthwhile to
   systematically accelerate */
EXTERNFN void psyco_turbo_code(PyCodeObject* code, int recursion);

/* call this to accelerate all frames currently executing the given code */
EXTERNFN void psyco_turbo_frames(PyCodeObject* code);


#endif /* _PROFILE_H */
