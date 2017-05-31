#include "idispatcher.h"
#include "../dispatcher.h"
#include "../codemanager.h"
#include "ipyencoding.h"


/***************************************************************/
 /***   the hard processor-dependent part of dispatching:     ***/
  /***   Unification.                                          ***/

#define RUNTIME_STACK(v)     getstack((v)->source)
#define RUNTIME_STACK_NONE   RunTime_StackNone


struct dmove_s {
  PsycoObject* po;
  int original_stack_depth;
  char* usages;   /* buffer: array of vinfo_t*, see ORIGINAL_VINFO() below */
  int usages_size;
  code_t* code_origin;
  code_t* code_limit;
  code_t* code;   /* only used by data_update_stack() */
  CodeBufferObject* private_codebuf;
};

static code_t* data_new_buffer(code_t* code, struct dmove_s* dm)
{
  /* creates a new buffer containing a copy of the already-written code */
  CodeBufferObject* codebuf;
  int codesize;
  if (dm->private_codebuf != NULL)
    {
      /* overflowing the regular (large) code buffer */
      psyco_emergency_enlarge_buffer(&code, &dm->code_limit);
      return code;
    }
  else
    {
      /* overflowing the small buffer, start a new (regular) one */
      codebuf = psyco_new_code_buffer(NULL, NULL, &dm->code_limit);
      codebuf->snapshot.fz_stuff.fz_stack_depth = dm->original_stack_depth;
      /* the new buffer should be at least as large as the old one */
      codesize = code - dm->code_origin;
      code = insn_code_label(codebuf->codestart);
      if (code + codesize > dm->code_limit)
        Py_FatalError("psyco: unexpected unify buffer overflow");
      /* copy old code to new buffer */
      memcpy(code, dm->code_origin, codesize+POST_CODEBUFFER_SIZE);
      dm->private_codebuf = codebuf;
#if PSYCO_DEBUG
      dm->code_origin = (code_t*) 0xCDCDCDCD;
#endif
      return code + codesize;
    }
}

#define ORIGINAL_VINFO(spos)    (*(vinfo_t**)(dm->usages + (            \
		extra_assert(0 <= (spos) && (spos) < dm->usages_size),  \
                (spos))))

static void data_original_table(vinfo_t* a, RunTimeSource bsource,
                                struct dmove_s* dm)
{
  /* called on each run-time vinfo_t in the FrozenPsycoObject.
     Record in the array dm->usages which vinfo_t is found at what position
     in the stack. Ignore the ones after dm->usages_size: they correspond to
     stack positions which will soon be deleted (because the stack will
     shrink). */
  if (RUNTIME_STACK(a) < dm->usages_size)
    ORIGINAL_VINFO(RUNTIME_STACK(a)) = a;
}

static void data_update_stack(vinfo_t* a, RunTimeSource bsource,
                              struct dmove_s* dm)
{
  PsycoObject* po = dm->po;
  code_t* code = dm->code;
  long dststack = getstack(bsource);
  long srcstack = getstack(a->source);
  vinfo_t* overridden;
  RunTimeSource osrc;
  
  /* check for values passing from no-reference to reference */
  if ((bsource & RunTime_NoRef) == 0) {  /* destination has ref */
    if ((a->source & RunTime_NoRef) == 0)   /* source has ref too */
      {
        /* remove the reference from 'a' because it now belongs
           to 'b' ('b->source' itself is in the frozen snapshot
           and must not be modified!) */
        a->source = remove_rtref(a->source);
      }
    else
      {
        /* create a new reference for 'b'. Note that if the same
           'a' is copied to several 'b's during data_update_stack()
           as is allowed by graph quotient detection in
           psyco_compatible(), then only the first copy will get
           the original reference owned by 'a' (if any) and for
           the following copies the following increfing code is
           executed as well. */
        INSN_rt_push(a->source);
	INSN_incref();
      }
  }
  /* 'a' must no longer own a reference at this point.
     The case of 'b' wanting no reference but 'a' having one
     is forbidden by psyco_compatible() because decrefing 'a'
     would potentially leave a freed pointer in 'b'. */
  extra_assert(!has_rtref(a->source));

  /* The operation below is: copy the value currently held by 'a'
     into the stack position 'dststack'. */
  if (dststack == RUNTIME_STACK_NONE || dststack == srcstack)
    ;  /* nothing to do */
  else
    {
      /* is there already a pending value at 'dststack'? */
      overridden = ORIGINAL_VINFO(dststack);
      if (overridden == NULL || RUNTIME_STACK(overridden) != dststack)
        goto can_save_only; /* no -- just save the new value to 'dststack'.
                               The case RUNTIME_STACK(overridden) != dststack
                               corresponds to a vinfo_t which has been moved
                               elsewhere in the mean time. */
      
      /* yes -- careful! We have to save the current value of
         'dststack' before we can overwrite it. */
      osrc = overridden->source;
      INSN_rt_push(osrc);
      osrc = set_rtstack_to_none(osrc);
      INSNPUSHED(1);
      overridden->source = set_rtstack_to(osrc, po->stack_depth);
      
    can_save_only:
      /* copy 'a' to 'dststack' */
      INSN_rt_push(a->source); INSNPUSHED(1);
      INSN_rt_pop(bsource);    INSNPOPPED(1);

      /* Now 'a' is at 'dststack' */
      a->source = RunTime_New1(dststack, false, false);
      ORIGINAL_VINFO(dststack) = a; /* 'a' is now there */
      
      if (code > dm->code_limit)
        /* oops, buffer overflow. Start a new buffer */
        code = data_new_buffer(code, dm);
      
    }
  dm->code = code;
}

static code_t* data_free_unused(code_t* code, struct dmove_s* dm,
                                vinfo_array_t* aa)
{
  /* decref any object that would be present in 'po' but not at all in
     the snapshot. Note that it is uncommon that this function actually
     finds any unused object at all. */
  int i = aa->count;
  while (i--)
    {
      vinfo_t* a = aa->items[i];
      if (a != NULL)
        {
          if (has_rtref(a->source))
            {
              PsycoObject* po = dm->po;
              code_t* saved_code;
              a->source = remove_rtref(a->source);
              
              saved_code = po->code;
              po->code = code;
              psyco_decref_rt(po, a);
              code = po->code;
              po->code = saved_code;

              if (code > dm->code_limit)
                /* oops, buffer overflow. Start a new buffer */
                code = data_new_buffer(code, dm);
            }
          if (a->array != NullArray)
            code = data_free_unused(code, dm, a->array);
        }
    }
  return code;
}

DEFINEFN
code_t* psyco_unify(PsycoObject* po, vcompatible_t* lastmatch,
                    CodeBufferObject** target)
{
  /* Update 'po' to match 'lastmatch', then jump to 'lastmatch'. */

  struct dmove_s dm;
  code_t* code = po->code;
  CodeBufferObject* target_codebuf = lastmatch->matching;
  int sdepth = get_stack_depth(&target_codebuf->snapshot);
#if PSYCO_DEBUG
  bool has_ccreg = HAS_CCREG(po);
#endif

  extra_assert(lastmatch->diff == NullArray);  /* unify with exact match only */
  psyco_assert_coherent(po);
  dm.usages_size = sdepth + sizeof(vinfo_t**);
  dm.usages = (char*) PyMem_MALLOC(dm.usages_size);
  if (dm.usages == NULL)
    OUT_OF_MEMORY();
  memset(dm.usages, 0, dm.usages_size);   /* set to all NULL */
  fz_find_runtimes(&po->vlocals, &target_codebuf->snapshot,
                   (fz_find_fn) &data_original_table,
                   &dm, false);

  dm.po = po;
  dm.original_stack_depth = po->stack_depth;
  dm.code_origin = code;
  dm.code_limit = po->codelimit == NULL ? code : po->codelimit;
  dm.private_codebuf = NULL;

  if (sdepth > po->stack_depth)
    {
      /* more items in the target stack (uncommon case).
         Let the stack grow. */
      STACK_CORRECTION(sdepth - po->stack_depth);
      po->stack_depth = sdepth;
    }

  /* update the stack */
  dm.code = code;
  fz_find_runtimes(&po->vlocals, &target_codebuf->snapshot,
                   (fz_find_fn) &data_update_stack,
                   &dm, true);
  code = dm.code;

  /* decref any object that would be present in 'po' but not at all in
     the snapshot (data_update_stack() has removed the 'ref' tag of all
     vinfo_ts it actually used from 'po') */
  code = data_free_unused(code, &dm, &po->vlocals);

  /* done */
  STACK_CORRECTION(sdepth - po->stack_depth);
  if (code > dm.code_limit)  /* start a new buffer if we wrote past the end */
    code = data_new_buffer(code, &dm);
#if PSYCO_DEBUG
  extra_assert(has_ccreg == HAS_CCREG(po));
#endif
  JUMP_TO((code_t*) target_codebuf->codestart);
  
  /* start a new buffer if the last JUMP_TO overflowed,
     but not if we had no room at all in the first place. */
  if (code > dm.code_limit && po->codelimit != NULL)
    {
      /* Note that the JMP instruction emitted by JUMP_TO() is
         position-independent (a property of the vm) */
      code = data_new_buffer(code, &dm);
      psyco_assert(code <= dm.code_limit);
    }
  
  PyMem_FREE(dm.usages);
  if (dm.private_codebuf == NULL)
    {
      Py_INCREF(target_codebuf);      /* no new buffer created */
      *target = target_codebuf;
    }
  else
    {
      SHRINK_CODE_BUFFER(dm.private_codebuf, code, "unify");
      *target = dm.private_codebuf;
      /* add a jump from the original code buffer to the new one */
      code = po->code;
      JUMP_TO((code_t*) dm.private_codebuf->codestart);
      dump_code_buffers();
    }
  PsycoObject_Delete(po);
  return code;
}
