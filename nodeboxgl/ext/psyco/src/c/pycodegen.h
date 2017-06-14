 /***************************************************************/
/*** Generic support code for Python-specific code generation  ***/
 /***************************************************************/

#ifndef _PYCODEGEN_H
#define _PYCODEGEN_H

#include "vcompiler.h"
#include <ipyencoding.h>


/* emit Py_INCREF(v) */
PSY_INLINE bool psyco_incref_v(PsycoObject* po, vinfo_t* v)
{
  if (!compute_vinfo(v, po)) return false;
  psyco_incref_nv(po, v);
  return true;
}

/* emit Py_DECREF(v) */
PSY_INLINE void psyco_decref_v(PsycoObject* po, vinfo_t* v)
{
  switch (gettime(v->source)) {
    
  case RunTime:
    psyco_decref_rt(po, v);
    break;

  case CompileTime:
    psyco_decref_c(po, (PyObject*) CompileTime_Get(v->source)->value);
    break;
  }
}


/* can eat a reference if we had one in the first place, and
   if no one else will require it (i.e. there is only one reference
   left to 'vi') */
PSY_INLINE bool eat_reference(vinfo_t* vi)
{
  if (has_rtref(vi->source) && vi->refcount == 1)
    {
      vi->source = remove_rtref(vi->source);
      return true;
    }
  else
    return false;
}

/* force a reference to be consumed */
PSY_INLINE void consume_reference(PsycoObject* po, vinfo_t* vi)
{
	if (!eat_reference(vi))
		psyco_incref_v(po, vi);
}

/* make sure we have a reference on 'vi' */
PSY_INLINE void need_reference(PsycoObject* po, vinfo_t* vi)
{
  if ((vi->source & (TimeMask | RunTime_NoRef)) == (RunTime | RunTime_NoRef))
    {
      vi->source = add_rtref(vi->source);
      psyco_incref_rt(po, vi);
    }
}


#endif /* _PYCODEGEN_H */
