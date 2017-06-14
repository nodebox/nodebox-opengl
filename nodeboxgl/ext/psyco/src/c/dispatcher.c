#include "dispatcher.h"
#include "codemanager.h"
#include "mergepoints.h"
#include "blockalloc.h"
#include "Python/pycompiler.h"   /* for pyc_data_xxx() */
#include "Objects/pobject.h"     /* for Psyco_SafelyDeleteVar() */
#include <idispatcher.h>


 /***************************************************************/
/***                       Snapshots                           ***/
 /***************************************************************/


#if !VLOCALS_OPC

/* Store-by-copy: this implementation is kept around for reference.
   See the "!VLOCALS_OPC" version of compatible_array().
*/

PSY_INLINE void fz_build(FrozenPsycoObject* fpo, vinfo_array_t* aa) {
  fpo->fz_vlocals = array_new(aa->count);
  duplicate_array(fpo->fz_vlocals, aa);
}

PSY_INLINE void fz_unfreeze(vinfo_array_t* aa, FrozenPsycoObject* fpo) {
  assert_cleared_tmp_marks(fpo->fz_vlocals);
  duplicate_array(aa, fpo->fz_vlocals);
  clear_tmp_marks(fpo->fz_vlocals);
}

PSY_INLINE void fz_release(FrozenPsycoObject* fpo) {
  array_delete(fpo->fz_vlocals, NULL);
}

      /* invariant: all snapshot.fz_vlocals in the fatlist have
         all their 'tmp' fields set to NULL. */
PSY_INLINE void fz_check_invariant(FrozenPsycoObject* fpo) {
  assert_cleared_tmp_marks(fpo->fz_vlocals);
}

PSY_INLINE void fz_restore_invariant(FrozenPsycoObject* fpo) {
  clear_tmp_marks(fpo->fz_vlocals);
}

PSY_INLINE int fz_top_array_count(FrozenPsycoObject* fpo) {
  return fpo->fz_vlocals->count;
}

static void fz_find_rt1(vinfo_array_t* bb, fz_find_fn callback,
                        void* extra, bool clear
#if ALL_CHECKS
                        , vinfo_array_t* aa
#endif
                        )
{
  int i = bb->count;
  while (i--)
    {
      vinfo_t* b = bb->items[i];
      if (b != NULL && b->tmp != NULL)
        {
#if ALL_CHECKS
          extra_assert(i < aa->count);
	  if (is_runtime(b->source))
            extra_assert(aa->items[i] == b->tmp);
#endif
	  if (is_runtime(b->source))
            (*callback)(b->tmp, b->source, extra);
          if (clear)
            b->tmp = NULL;  /* don't consider the same 'b' more than once */
          if (b->array != NullArray)
	    fz_find_rt1(b->array, callback, extra, clear
#if ALL_CHECKS
                        , aa->items[i]->array
#endif
                        );
        }
    }
}

DEFINEFN void fz_find_runtimes(vinfo_array_t* aa, FrozenPsycoObject* fpo,
                               fz_find_fn callback, void* extra, bool clear)
{
  fz_find_rt1(fpo->fz_vlocals, callback, extra, clear
#if ALL_CHECKS
              , aa
#endif
              );
}


#else /* if VLOCALS_OPC */

#define COMPRESS_COMPILETIME_SUBITEMS    0


struct vcilink_s {
  int time;
  union {
    vinfo_t* preva;
    vinfo_t** fix;
    void* data;
  } v;
  struct vcilink_s* next;
};

BLOCKALLOC_STATIC(vci, struct vcilink_s, 128)

typedef struct {
  /* pointers to an internal buffer for the creation of the pseudo-code
     copies, as well as for lookups */
  signed char* buf_begin;
  signed char* buf_end;
  signed char* buf_opc;     /* current opcode position */
  Source* buf_args;          /* current opargs position */
  int tmp_counter;            /* for links */
  struct vcilink_s* vcilink;   /* pending links during decompression */
  struct vcilink_s sentinel;
} vcompat_internal_t;

/* XXX Argh, a global variable -- this is (just) tolerable because the
   algorithms depending on it are not re-entrent anyway. This lets us
   share a global all-purpose buffer between the pseudo-code creation
   and the lookups. */
static vcompat_internal_t cmpinternal = { NULL, NULL };

static signed char* fz_internal_copy(vcompat_internal_t* current, int nsize)
{
  int opc_size = current->buf_end - current->buf_opc;
  signed char* buf = (signed char*) PyMem_MALLOC(nsize);
  if (buf == NULL)
    OUT_OF_MEMORY();
  memcpy(buf, current->buf_begin,
         ((signed char*) current->buf_args) - current->buf_begin);
  memcpy(buf + nsize - opc_size, current->buf_opc, opc_size);
  return buf;
}

static void fz_internal_expand(void)
{
  signed char* nbuf;
  int opc_size = cmpinternal.buf_end - cmpinternal.buf_opc;
  int arg_size = ((signed char*) cmpinternal.buf_args) - cmpinternal.buf_begin;
  int nsize = (cmpinternal.buf_end - cmpinternal.buf_begin) * 3 / 2;
  if (nsize < 64) nsize = 64;
  nbuf = fz_internal_copy(&cmpinternal, nsize);
  if (cmpinternal.buf_begin != cmpinternal.buf_end)
    PyMem_FREE(cmpinternal.buf_begin);
  cmpinternal.buf_begin = nbuf;
  cmpinternal.buf_end = nbuf + nsize;
  cmpinternal.buf_opc = cmpinternal.buf_end - opc_size;
  cmpinternal.buf_args = (Source*)(nbuf + arg_size);
}

#define FZ_OPC_EXT      (-1)
#define FZ_OPC_NULL     (-2)
#define FZ_OPC_LINK     (-3)   /* and the following negative numbers */

/* Note: the pseudo-code is built in left-to-right array order,
   but it is intended to be read backwards, thus uncompression creates
   the arrays right-to-left. */
PSY_INLINE void fz_putarg(Source arg)
{
  if (cmpinternal.buf_opc < (signed char*) (cmpinternal.buf_args+1))
    fz_internal_expand();
  *cmpinternal.buf_args++ = arg;
}

PSY_INLINE void fz_putopc(int opc)
{
  if (!(-128 <= opc && opc < 128))
    {
      fz_putarg((Source) opc);
      opc = FZ_OPC_EXT;
    }
  if (cmpinternal.buf_opc == (signed char*) cmpinternal.buf_args)
    fz_internal_expand();
  *--cmpinternal.buf_opc = opc;
}

#if COMPRESS_COMPILETIME_SUBITEMS
static void fz_compress(vinfo_array_t* aa, bool nolinks)
{
  int i;
  int length = aa->count;
  /*while (length > 0 && aa->items[length-1] == NULL)
    length--;  ---- invalid optimization ---- */
  for (i=0; i<length; i++)
    {
      vinfo_t* a = aa->items[i];
      if (a == NULL) {
        fz_putopc(FZ_OPC_NULL);   /* emit FZ_OPC_NULL */
      }
      else if (a->tmp != NULL) {
        int prevcounter = (int) a->tmp;   /* already seen, emit a link */
        fz_putopc(FZ_OPC_LINK - (cmpinternal.tmp_counter-prevcounter));
      }
      else {
        bool nosublinks = nolinks;
        int length;
        Source arg = a->source;
        if (is_compiletime(arg))
          {
            sk_incref(CompileTime_Get(arg));
            nosublinks = true;
          }
        ++cmpinternal.tmp_counter;
        if (!nolinks)
          a->tmp = (vinfo_t*) cmpinternal.tmp_counter;
        length = a->array->count;
        if (length)    /* avoid recursive call if unneeded */
          fz_compress(a->array, nosublinks);  /* store the subarray */
        fz_putarg(a->source);    /* store the 'source' field */
        fz_putopc(length);      /* store the length of the subarray */
      }
    }
}
#else   /* !COMPRESS_COMPILETIME_SUBITEMS */
static void fz_compress(vinfo_array_t* aa)
{
  int i;
  int length = aa->count;
  /*while (length > 0 && aa->items[length-1] == NULL)
    length--;  ---- invalid optimization ---- */
  for (i=0; i<length; i++)
    {
      vinfo_t* a = aa->items[i];
      if (a == NULL) {
        fz_putopc(FZ_OPC_NULL);   /* emit FZ_OPC_NULL */
      }
      else if (a->tmp != NULL) {
        int prevcounter = (int) a->tmp;   /* already seen, emit a link */
        fz_putopc(FZ_OPC_LINK - (cmpinternal.tmp_counter-prevcounter));
      }
      else {
        int length;
        Source arg;
        a->tmp = (vinfo_t*) (++cmpinternal.tmp_counter);
        arg = a->source;
        if (is_compiletime(arg))
          {
            sk_incref(CompileTime_Get(arg));
            length = 0;
          }
        else
          {
            length = a->array->count;
            if (length)    /* avoid recursive call if unneeded */
              fz_compress(a->array);  /* store the subarray */
          }
        fz_putarg(a->source);    /* store the 'source' field */
        fz_putopc(length);      /* store the length of the subarray */
      }
    }
}
#endif  /* COMPRESS_COMPILETIME_SUBITEMS */
/* Compression note: if we implement sharing of common initial segments
   (which could save another 50% memory) we get better results by storing
   the 'source' field *before* its sub-array. This will complicate
   compatible_array() a bit. */

PSY_INLINE Source fz_getarg(void)
{
  return *--cmpinternal.buf_args;
}

PSY_INLINE int fz_getopc(void)
{
  int result = *cmpinternal.buf_opc++;
  if (result == FZ_OPC_EXT)
    result = (int) fz_getarg();
  return result;
}

static void fz_pushstack(int opc, void* ndata)
{
  int ntime = cmpinternal.tmp_counter + (FZ_OPC_LINK-opc);
  struct vcilink_s** q;
  struct vcilink_s* p = psyco_llalloc_vci();
  p->time = ntime;
  p->v.data = ndata;
  
  /* Record the pending link by inserting it inon the vcilink linked list.
     'ntime' is the value that tmp_counter will have when the pending
     item is found, so currently 'ntime >= tmp_counter'.
     This linked list is sorted against the time, smallest time first. */
  q = &cmpinternal.vcilink;
  while ((*q)->time < ntime)
    q = &(*q)->next;
  p->next = *q;   /* insert new item at the correct position */
  *q = p;
}

static void fz_uncompress(vinfo_array_t* result)
{
  int i = result->count;
  while (i--)
    {
      vinfo_t* a;
      int opc = fz_getopc();
      if (opc >= 0) {        /* new item, potentially with its sub-array */
        a = vinfo_new_skref(fz_getarg());
        if (opc != 0) {       /* test to make the common path (opc==0) faster */
          a->array = array_new(opc);
          fz_uncompress(a->array);
        }
      }
      else if (opc == FZ_OPC_NULL) {   /* NULL */
        continue;  /* there is already NULL in result->items[i] */
      }
      else {       /* link to an item not built yet */
        fz_pushstack(opc, &result->items[i]);
        continue;
      }

      /* At this point we have a real item to store into the array */
      while (cmpinternal.tmp_counter == cmpinternal.vcilink->time)
        {
          struct vcilink_s* p = cmpinternal.vcilink;
          cmpinternal.vcilink = p->next;
          /* resolve link */
          vinfo_incref(a);
          *p->v.fix = a;
          psyco_llfree_vci(p);
        }
      cmpinternal.tmp_counter++;
      result->items[i] = a;
    }
}

static void fz_parse(int length, bool clear)
{ /* highly simplified version of fz_uncompress() that does nothing */
  extra_assert(length >= 0);
  while (length--)
    {
      int opc = fz_getopc();
      if (opc >= 0)
        {
          Source arg = fz_getarg();
          fz_parse(opc, clear);
          if (clear && is_compiletime(arg))
            sk_decref(CompileTime_Get(arg));
        }
    }
}

static void fz_find_rt1(vinfo_array_t* aa, int length,
                        fz_find_fn callback, void* extra)
{ /* simplified version of fz_uncompress() that does not build anything */
  extra_assert(length >= 0);
  while (length--)
    {
      int opc = fz_getopc();
      if (opc >= 0)
        {
          vinfo_t* a;
          Source source = fz_getarg();
          if (is_compiletime(source))
            {
              /* no run-time value should exist under a compile-time one */
              extra_assert(aa == NULL || length < aa->count);
              if (opc > 0)
                fz_find_rt1(NULL, opc, NULL, NULL);
            }
          else
            {
              extra_assert(aa != NULL && length < aa->count);
              a = aa->items[length];
              if (is_runtime(source))
                (*callback)(a, source, extra);
              if (opc > 0)
                fz_find_rt1(a->array, opc, callback, extra);
            }
        }
    }
}

PSY_INLINE void fz_load_fpo(FrozenPsycoObject* fpo) {
  cmpinternal.buf_opc  = (signed char*) fpo->fz_vlocals_opc;
  cmpinternal.buf_args =                fpo->fz_vlocals_opc;
}

DEFINEFN void fz_find_runtimes(vinfo_array_t* aa, FrozenPsycoObject* fpo,
                               fz_find_fn callback, void* extra, bool clear)
{
  fz_load_fpo(fpo);
  fz_find_rt1(aa, fz_getopc(), callback, extra);
}

PSY_INLINE void fz_build(FrozenPsycoObject* fpo, vinfo_array_t* aa)
{
  int opc_size, arg_size;
  signed char* nbuf;
  cmpinternal.buf_opc = cmpinternal.buf_end;
  cmpinternal.buf_args = (Source*) cmpinternal.buf_begin;
  cmpinternal.tmp_counter = 0;
  clear_tmp_marks(aa);
#if COMPRESS_COMPILETIME_SUBITEMS
  fz_compress(aa, false);
#else
  fz_compress(aa);
#endif
  fz_putopc(aa->count);
  opc_size = cmpinternal.buf_end - cmpinternal.buf_opc;
  arg_size = ((signed char*) cmpinternal.buf_args) - cmpinternal.buf_begin;
  psyco_memory_usage += arg_size + opc_size + sizeof(CodeBufferObject);
  nbuf = fz_internal_copy(&cmpinternal, arg_size + opc_size);
  fpo->fz_vlocals_opc = (Source*) (nbuf + arg_size);
}

PSY_INLINE void fz_load_fpo_stack(FrozenPsycoObject* fpo) {
  fz_load_fpo(fpo);
  cmpinternal.tmp_counter = 0;
  cmpinternal.vcilink = &cmpinternal.sentinel;
  cmpinternal.sentinel.time = INT_MAX;   /* sentinel */
}

PSY_INLINE int fz_top_array_count(FrozenPsycoObject* fpo) {
  int result;
  if (fpo->fz_vlocals_opc == NULL)
    return 0;
  fz_load_fpo(fpo);
  result = fz_getopc();
  extra_assert(result >= 0);
  return result;
}

PSY_INLINE void fz_unfreeze(vinfo_array_t* aa, FrozenPsycoObject* fpo) {
  fz_load_fpo_stack(fpo);
  aa->count = fz_getopc();
  fz_uncompress(aa);
  /* no more pending link should be left */
  extra_assert(cmpinternal.vcilink == &cmpinternal.sentinel);
}

PSY_INLINE void fz_release(FrozenPsycoObject* fpo) {
  if (fpo->fz_vlocals_opc != NULL)
    {
      fz_load_fpo(fpo);
      fz_parse(fz_getopc(), true);  /* find the beginning of the pseudo-code */
      PyMem_FREE(cmpinternal.buf_args);
    }
}

PSY_INLINE void fz_check_invariant(FrozenPsycoObject* fpo) {
}

PSY_INLINE void fz_restore_invariant(FrozenPsycoObject* fpo) {
}


#endif /* VLOCALS_OPC */


#if !ALL_STATIC
 DEFINEFN int psyco_top_array_count(FrozenPsycoObject* fpo)  /*for psyco.c*/
          { return fz_top_array_count(fpo); }
#endif


 /***************************************************************/

DEFINEFN
void fpo_build(FrozenPsycoObject* fpo, PsycoObject* po)
{
  psyco_assert_coherent1(po, false);
  clear_tmp_marks(&po->vlocals);
  fz_build(fpo, &po->vlocals);
  fpo->fz_stuff.fz_stack_depth = po->stack_depth;
  SAVE_PROCESSOR_FROZENOBJECT(fpo, po);
  fpo->fz_pyc_data = pyc_data_new(&po->pr);
}

DEFINEFN
void fpo_release(FrozenPsycoObject* fpo)
{
  if (fpo->fz_pyc_data != NULL)
    pyc_data_delete(fpo->fz_pyc_data);
  fz_release(fpo);
}

static void fpo_find_regs_array(vinfo_array_t* source, PsycoObject* po)
{
#if HAVE_CCREG
  condition_code_t cc;
#endif
  int i = source->count;
  while (i--)
    {
      vinfo_t* a = source->items[i];
      if (a != NULL)
        {
          Source src = a->source;
#if REG_TOTAL > 0
          if (is_runtime(src) && !is_reg_none(src))
            REG_NUMBER(po, getreg(src)) = a;
          else
#endif
#if HAVE_CCREG
            if ((cc = psyco_vsource_cc(src)) != CC_ALWAYS_FALSE)
              po->ccregs[INDEX_CC(cc)] = a;
            else
#endif
              /* nothing */ ;
          if (a->array != NullArray)
            fpo_find_regs_array(a->array, po);
        }
    }
}

DEFINEFN
PsycoObject* fpo_unfreeze(FrozenPsycoObject* fpo)
{
  /* rebuild a PsycoObject from 'this' */
  PsycoObject* po = PsycoObject_New(fz_top_array_count(fpo));
  po->stack_depth = get_stack_depth(fpo);
  RESTORE_PROCESSOR_FROZENOBJECT(fpo, po);
  fz_unfreeze(&po->vlocals, fpo);
  fpo_find_regs_array(&po->vlocals, po);
  frozen_copy(&po->pr, fpo->fz_pyc_data);
  pyc_data_build(po, psyco_get_merge_points(po->pr.co, -1));
  psyco_assert_coherent(po);
  return po;
}


/*****************************************************************
 * Respawning is restoring a frozen compiler state into a live
 * PsycoObject and restarting the compilation. It will produce
 * exactly the same code up to a given point. This point was
 * a jump in the run-time code, pointing to code that we did
 * not compile yet. The purpose of 'replaying' the compilation
 * is to rebuild exactly the same state as the compiler had when
 * it emitted the jump instruction in the first place. At this
 * point we can go on with the real compilation of the missing
 * code.
 *
 * This is all based on the idea that we want to avoid tons
 * of copies of PsycoObjects all around for all pending
 * compilation branches, and there are a lot of them -- e.g. all
 * instructions that could trigger an exception have such a
 * (generally uncompiled) branch.
 *****/

typedef struct respawn_s {
  CodeBufferObject* self;
  void* write_jmp;
  int respawn_cnt;
  CodeBufferObject* respawn_from;
} respawn_t;

static code_t* do_respawn(respawn_t* rs)
{
  /* called when entering a not-compiled branch requiring a respawn */
  code_t* code;
  CodeBufferObject* firstcodebuf;
  CodeBufferObject* codebuf;
  PsycoObject* po;

  /* we might have a chain of code buffers, each containing a conditional
     jump to the next one. It ends with a proxy (not-yet-compiled) calling
     the function do_respawn().
     
     +----------+
     |  ...     |
     |  Jcond ----------->  +----------+
     |  ...     |           |  ...     |
     +----------+           |  Jcond ----------->   +-----------------+
                            |  ...     |            | CALL do_respawn |
                            +----------+            +-----------------+

     The structure 'rs' is stored in the last block (the proxy).
     'rs->respawn_from' is the previous code buffer.
     'rs->respawn_from->snapshot.fz_respawned_from' is the previous one.
     etc.
  */
  int respawn_cnt = rs->respawn_cnt;
  /* find the first code buffer in the chain */
  for (firstcodebuf = rs->respawn_from;
       firstcodebuf->snapshot.fz_respawned_from != NULL;
       firstcodebuf = firstcodebuf->snapshot.fz_respawned_from)
    respawn_cnt = firstcodebuf->snapshot.fz_respawned_cnt;
  /* respawn there */
  po = fpo_unfreeze(&firstcodebuf->snapshot);
  
  codebuf = psyco_new_code_buffer(NULL, NULL, &po->codelimit);
  codebuf->snapshot.fz_stuff.respawning = rs;
  codebuf->snapshot.fz_respawned_cnt = rs->respawn_cnt;
  codebuf->snapshot.fz_respawned_from = firstcodebuf;
  po->code = insn_code_label(codebuf->codestart);
  /* respawn by restarting the Python compiler at the beginning of the
     instruction where it left. It will probably re-emit a few machine
     instructions -- not needed, they will be trashed, but this has
     rebuilt the correct PsycoObject state. This occurs when eventually
     a positive detect_respawn() is issued. */
  po->respawn_cnt = - respawn_cnt;
  po->respawn_proxy = codebuf;

  code = GLOBAL_ENTRY_POINT(po);
  
  SHRINK_CODE_BUFFER(codebuf, code, "respawned");
  /* make sure detect_respawn() succeeded */
  psyco_assert(codebuf->snapshot.fz_respawned_from == rs->respawn_from);

  /* fix the jump to point to 'codebuf->codestart' */
  change_cond_jump_target(rs->write_jmp, (code_t*)codebuf->codestart);
  
  /* cannot Py_DECREF(cp->self) because the current function is returning into
     that code now, but any time later is fine: use the trash of codemanager.c */
  psyco_trash_object((PyObject*) rs->self);
  dump_code_buffers();
  /* XXX don't know what to do with this reference to codebuf */
  return codebuf->codestart;
}

DEFINEFN
void psyco_respawn_detected(PsycoObject* po)
{
  /* this is called when detect_respawn() succeeds. We can now proceed
     to the next code block in the picture above. When we reach the
     last one, it means we are about to compile the 'special' branch of
     a conditional jump -- the one that is not compiled yet.
  */
  CodeBufferObject* codebuf = po->respawn_proxy;
  CodeBufferObject* current = codebuf->snapshot.fz_respawned_from;
  respawn_t* rs = codebuf->snapshot.fz_stuff.respawning;

  /* 'codebuf' is the new block we are writing.
     'current' is the block we are currently respawning.
     'rs->respawn_from' is the last block before the proxy calling
        do_respawn(). */
  if (current == rs->respawn_from)
    {
      /* respawn finished */
      extra_assert(fz_top_array_count(&codebuf->snapshot) == 0);
      fpo_build(&codebuf->snapshot, po);
    }
  else
    {
      /* proceed to the next block */
      CodeBufferObject* nextblock;
      int respawn_cnt = rs->respawn_cnt;
      for (nextblock = rs->respawn_from;
           nextblock->snapshot.fz_respawned_from != current;
           nextblock = nextblock->snapshot.fz_respawned_from)
        respawn_cnt = nextblock->snapshot.fz_respawned_cnt;
      codebuf->snapshot.fz_respawned_from = nextblock;
      po->respawn_cnt = - respawn_cnt;
    }
  /* restart at the beginning of the buffer, overriding the code written
     so far. XXX when implementing freeing of code, be careful that this
     lost code does not looses references to other objects as well.
     Use is_respawning() to bypass the creation of all references when
     compiling during respawn. */
  po->code = (code_t*) codebuf->codestart;
  INIT_CODE_EMISSION(po->code);
}

DEFINEFN
void* psyco_prepare_respawn_ex(PsycoObject* po, condition_code_t jmpcondition,
                               void* fn, int extrasize)
{
  /* ignore calls to psyco_prepare_respawn() while currently respawning */
  if (!is_respawning(po))
    {
      char* closure;
      respawn_t* rs;
      code_t* calling_code;
      code_t* calling_limit;
      code_t* limit;
      CodeBufferObject* codebuf = psyco_new_code_buffer(NULL, NULL, &limit);
  
      extra_assert((int)jmpcondition < CC_TOTAL);

      /* the proxy contains only a jump to do_respawn,
         followed by a respawn_t structure */
      calling_code = po->code;
      calling_limit = po->codelimit;
      po->code = insn_code_label(codebuf->codestart);
      po->codelimit = limit;
      closure = (char*) psyco_call_code_builder(po, fn, true, SOURCE_DUMMY);
      rs = (respawn_t*) (closure+extrasize);
      SHRINK_CODE_BUFFER(codebuf, (code_t*)(rs+1), "respawn");
      /* fill in the respawn_t structure */
      extra_assert(po->respawn_proxy != NULL);
      rs->self = codebuf;
      rs->respawn_cnt = po->respawn_cnt;
      rs->respawn_from = po->respawn_proxy;

      /* write the jump to the proxy */
      po->code = calling_code;
      po->codelimit = calling_limit;
      psyco_resolved_cc(po, INVERT_CC(jmpcondition)); /* no jump => cond false */
      rs->write_jmp = conditional_jump_to(po, (code_t*)codebuf->codestart,
                                          jmpcondition);
      dump_code_buffers();
      return closure;
    }
  else
    {
      /* respawning: come back at the
         beginning of the trash memory for
         the next instructions */
      po->code = (code_t*) po->respawn_proxy->codestart;
      INIT_CODE_EMISSION(po->code);
      return NULL;
    }
}

DEFINEFN
bool psyco_prepare_respawn(PsycoObject* po, condition_code_t jmpcondition)
{
  if (detect_respawn(po)) return true;
  psyco_prepare_respawn_ex(po, jmpcondition, &do_respawn, 0);
  return false;
}

DEFINEFN
code_t* psyco_do_respawn(void* arg, int extrasize)
{
  respawn_t* rs = (respawn_t*)(((char*) arg) + extrasize);
  return do_respawn(rs);
}

DEFINEFN
code_t* psyco_dont_respawn(void* arg, int extrasize)
{
  respawn_t* rs = (respawn_t*)(((char*) arg) + extrasize);
  return resume_after_cond_jump(rs->write_jmp);
}

DEFINEFN
int runtime_NON_NULL_f(PsycoObject* po, vinfo_t* vi)
{
  condition_code_t cc = integer_NON_NULL(po, vi);
  return cc == CC_ERROR ? -1 : runtime_condition_f(po, cc);
}

DEFINEFN
int runtime_NON_NULL_t(PsycoObject* po, vinfo_t* vi)
{
  condition_code_t cc = integer_NON_NULL(po, vi);
  return cc == CC_ERROR ? -1 : runtime_condition_t(po, cc);
}

DEFINEFN
int runtime_in_bounds(PsycoObject* po, vinfo_t* vi,
                      long lowbound, long highbound)
{
  condition_code_t cc;
  if (highbound == LONG_MAX)
    {
      if (lowbound == LONG_MIN)
        return 1;
      cc = integer_cmp_i(po, vi, lowbound, Py_GE);
    }
  else if (lowbound == 0)
    {
      cc = integer_cmp_i(po, vi, highbound, Py_LE | COMPARE_UNSIGNED);
    }
  else
    {
      if (lowbound != LONG_MIN)
        {
          cc = integer_cmp_i(po, vi, lowbound, Py_GE);
          if (cc == CC_ERROR)
            return -1;
          if (!runtime_condition_t(po, cc))
            return 0;
        }
      cc = integer_cmp_i(po, vi, highbound, Py_LE);
    }
  return cc == CC_ERROR ? -1 : runtime_condition_t(po, cc);
}


DEFINEFN
void PsycoObject_EmergencyCodeRoom(PsycoObject* po)
{
  if (!is_respawning(po))
    {
      /* non-respawning case: start a new buffer, and code a JMP at
         the end of the current buffer. Note that it is exceptional
         to reach this point. Normally, pycompiler.c regularly checks
         that we are not reaching the end of the buffer, and if so,
         pauses compilation. */
      psyco_emergency_enlarge_buffer(&po->code, &po->codelimit);
    }
  else
    {
      /* respawning case: trash everything written so far */
      po->code = (code_t*) po->respawn_proxy->codestart;
      INIT_CODE_EMISSION(po->code);
    }
}


/*****************************************************************/

#if !VLOCALS_OPC

/* This implementation should probably not be used any more, but it
   is kept around for reference. Once you understand the comparison
   algorithm below you can read its more obscure implementation of
   the VLOCALS_OPC case.
*/
static bool compatible_array(vinfo_array_t* aa, vinfo_array_t* bb,
                             vinfo_array_t** result)
{
  /* 'aa' is the array from the live PsycoObject. 'bb' is from the snapshop.
     Test for compatibility. More precisely, it must be allowable for the
     living state 'aa' to jump back to the code already produced for the
     state 'bb'. There might be more information in 'aa' than in 'bb' (which
     will then just be discarded), but the converse is not allowable.
     Moreover, if two slots in the arrays point to the same vinfo_t in 'bb',
     they must also do so in 'aa' because the code compiled from 'bb' might
     have used this fact. Conversely, shared pointers in 'aa' need *not* be
     shared any more in 'bb'.

     The sharing rule only applies to run-time values: for compile-time and
     virtual-time values, being shared or not is irrelevant to the compilation
     process.
     
     Return value of compatible_array(): false if incompatible, otherwise
     fills the 'result' array with the variables to un-promote.
  */
  int i;
  int count = bb->count;
  if (aa->count != count)
    {
      if (aa->count < count)   /* array too short; ok only if the extra items */
	{                      /*   in 'bb' are all NULL.                     */
	  for (i=aa->count; i<count; i++)
	    if (bb->items[i] != NULL)
	      return false;   /* differs */
	  count = aa->count;
	}
      else  /* array too long */
        {
#if 0
          /* the extra items in 'aa' must pass the test (b == NULL) below. */
          for (i=aa->count; i>count; )
            {
              vinfo_t* a = aa->items[--i];
              if (a != NULL && is_compiletime(a->source) &&
                  ((KNOWN_SOURCE(a)->refcount1_flags & SkFlagFixed) != 0))
                return false;  /* incompatible */
            }
#else
          /* the extra items in 'aa' must all be NULL. This is not strictly
             necessary for a compatibility (the above condition is more
             precise) but I guess that you get better results this way,
             because you have more information for a recompilation.
             XXX This assumption should be tested.
             XXX What about requiring that no NULL goes non-NULL in the
                 rest of the array as well? */
	  for (i=aa->count; i>count; )
	    if (aa->items[--i] != NULL)
	      return false;   /* differs */
#endif
	}
    }
  for (i=0; i<count; i++)
    {
      vinfo_t* a = aa->items[i];
      vinfo_t* b = bb->items[i];
      if (b == NULL)
        {
          /* if b == NULL, any value in 'a' is ok --
             with the exception of a fixed compile-time value, as
             created by a promotion. Without the following test,
             Psyco sometimes emits an infinite loop because the
             PsycoObject after promotion is found to be compatible
             with itself just before promotion. */
          if (a != NULL && is_compiletime(a->source) &&
              ((KNOWN_SOURCE(a)->refcount1_flags & SkFlagFixed) != 0))
            goto incompatible;
        }
      else
	{
          long diff;
          /* we store in the 'tmp' fields of the 'bb' arrays pointers to the
             vinfo_t that matched in 'aa'. We assume that all 'tmp' fields
             are NULL initially. If, walking in the 'bb' arrays, we encounter
             the same 'b' several times, we use these 'tmp' pointers to make
             sure they all matched the same 'a'. */
	  if (b->tmp != NULL)
	    {
              /* This 'b' has already be seen. */
	      if (b->tmp == a)
                continue;  /* quotient graph */

              /* at this point, the graph 'aa' is not a quotient of the
                 graph 'bb', i.e. two nodes are shared in 'bb' but not
                 in 'aa'. This is not acceptable if it is a run-time
                 value, or if it is a virtual-time value whose identity
                 matters. */
              switch (gettime(b->source))
                {
                case RunTime:
                  goto incompatible;

                case VirtualTime:
                  if (SVIRTUAL_MUTABLE(VirtualTime_Get(b->source)))
                    goto incompatible;
                  break;

                default:
                  ;
                }
	    }
          
          /* A new 'b', let's check if its 'a' matches. */
          if (a == NULL)
            goto incompatible;  /* NULL not compatible with non-NULL */
          b->tmp = a;
          diff = ((long)a->source) ^ ((long)b->source);
          if (diff != 0)
            {
              if ((diff & TimeMask) != 0)
                goto incompatible;  /* not the same TIME_MASK */
              if (is_runtime(a->source))
                {
                  if ((diff & RunTime_NoRef) != 0)
                    {
                      /* from 'with ref' to 'without ref' or vice-versa:
                         a source in 'a' with reference cannot pass for
                         a source in 'b' without reference */
                      if ((a->source & RunTime_NoRef) == 0)
                        goto incompatible;
                    }
                }
              else
                {
                  if (is_virtualtime(a->source))
                    goto incompatible;  /* different virtual sources */
                  if (KNOWN_SOURCE(a)->value != KNOWN_SOURCE(b)->value)
                    {
                      if ((KNOWN_SOURCE(b)->refcount1_flags &
                           SkFlagFixed) != 0)
                        goto incompatible;  /* b's value is fixed */
                      if ((KNOWN_SOURCE(a)->refcount1_flags &
                           SkFlagFixed) != 0 && KNOWN_SOURCE(a)->value == 0)
                        goto incompatible;  /* hack: */
                          /* fixed known-to-be-zero values have a special
                             role to play with local variables: undefined
                             variables. These must *never* be un-promoted
                             to run-time, because we will get a NULL
                             pointer and a segfault. Argh. */
                      else {
                        /* approximative match, might un-promote 'a' from
                           compile-time to run-time. */
                        /*fprintf(stderr, "psyco: compatible_array() with vinfo_t* a=%p, b=%p\n", a, b);*/
                        int i, ocount = (*result)->count;
                        /* do not add several time the same value to the array */
                        for (i=0; i<ocount; i++)
                          if ((*result)->items[i] == a)
                            break;
                        if (i==ocount)
                          {
                            *result = array_grow1(*result, ocount+1);
                            (*result)->items[ocount] = a;
                          }
                      }
                    }
                }
            }
          if (a->array != b->array) /* can only be equal if both ==NullArray */
            {
              if (is_compiletime(a->source))
                {
                  /* For compile-time values we don't bother comparing
                     subarrays, because they only have a caching role
                     in this case; they should never contain information
                     different from what psyco_get_field() can load or
                     reload from immutable data. */
#if PSYCO_DEBUG
                  /* we just verify that there are only compile-time
                     subitems. */
                  int j;
                  for (j=0; j<a->array->count; j++)
                    extra_assert(a->array->items[j] == NULL ||
                                 is_compiletime(a->array->items[j]->source));
                  for (j=0; j<b->array->count; j++)
                    extra_assert(b->array->items[j] == NULL ||
                                 is_compiletime(b->array->items[j]->source));
#endif
                }
              else
                if (!compatible_array(a->array, b->array, result))
                  goto incompatible;
            }
        }
    }
  return true;

 incompatible:     /* we have to reset the 'tmp' fields to NULL,
                      but only as far as we actually progressed */
  for (; i>=0; i--)
    if (bb->items[i] != NULL)
      {
	bb->items[i]->tmp = NULL;
	if (bb->items[i]->array != NullArray)
	  clear_tmp_marks(bb->items[i]->array);
      }
  return false;
}

PSY_INLINE bool fz_compatible_array(vinfo_array_t* aa, FrozenPsycoObject* fpo,
                                vcompatible_t* result) {
  return compatible_array(aa, fpo->fz_vlocals, &result->diff);
}


#else /* if VLOCALS_OPC */

/* forward */
static bool compatible_array(vinfo_array_t* aa, int count,
                             vinfo_array_t** result, vinfo_array_t* reference,
                             int recdepth);
#if COMPRESS_COMPILETIME_SUBITEMS
static void skip_compatible_array(int count);
#endif

static bool compatible_vinfo(vinfo_t* a, Source bsource, int bcount,
                             vinfo_array_t** result, vinfo_t* aref,
                             int recdepth)
{
  /* Check if 'a' matches 'bsource'. */
  long diff;
  /*bool skip_subarray = false;*/

  /* If 'aref!=a' then 'aref' is a vinfo_t* that already passed the test
     against the same 'bsource'. In this case there is an extra test:
     as the two nodes 'a' and 'aref' are not shared in 'aa', but shared
     in 'bb', then they must not be run-time sources, because the
     compiler could have used this fact when compiling from 'bb'
     (typically, this single value was in a single register).  Nor can
     they be mutable virtual-time values, for identity reasons. */
  if (a != aref)
    switch (gettime(bsource))
      {
      case RunTime:
        return false;

      case VirtualTime:
        if (SVIRTUAL_MUTABLE(VirtualTime_Get(bsource)))
          return false;
        break;

      default:
        ;
      }

  /* invariant */
  extra_assert(cmpinternal.tmp_counter <= cmpinternal.vcilink->time);

  if (a == NULL)
    return false;  /* NULL not compatible with non-NULL */
  diff = ((long)a->source) ^ ((long)bsource);
  if (diff != 0)
    {
      if ((diff & TimeMask) != 0)
        return false;  /* not the same TIME_MASK */
      
      switch (gettime(a->source)) {
        
      case RunTime:
        if ((diff & (RunTime_NoRef|RunTime_NonNeg|RunTime_Megamorphic)) != 0)
          {
            /* from 'with ref' to 'without ref' or vice-versa:
               a source in 'a' with reference cannot pass for
               a source in 'b' without reference */
            if ((a->source & RunTime_NoRef) == 0 &&
                (  bsource & RunTime_NoRef) != 0)
              return false;
            /* from 'non-negative' to 'possibly negative' or vice-versa:
               a source in 'a' which may be negative cannot pass for
               a source in 'b' which cannot */
            if ((a->source & RunTime_NonNeg) == 0 &&
                (  bsource & RunTime_NonNeg) != 0)
              return false;
            /* a source in 'a' which is flagged as megamorphic should
               not fall back to a source in 'b' which is not */
            if ((a->source & RunTime_Megamorphic) != 0 &&
                (  bsource & RunTime_Megamorphic) == 0)
              return false;
          }
        break;

      case CompileTime:
        if (CompileTime_Get(a->source)->value != CompileTime_Get(bsource)->value)
          {
            if ((CompileTime_Get(bsource)->refcount1_flags &
                 SkFlagFixed) != 0)
              return false;  /* b's value is fixed */
            if ((CompileTime_Get(a->source)->refcount1_flags &
                 SkFlagFixed) != 0 && CompileTime_Get(a->source)->value == 0)
              return false;  /* hack: */
            /* fixed known-to-be-zero values have a special
               role to play with local variables: undefined
               variables. These must *never* be un-promoted
               to run-time, because we will get a NULL
               pointer and a segfault. Argh. */
            else {
              /* approximative match, might un-promote 'a' from
                 compile-time to run-time. */
              int i, ocount = (*result)->count;
              /* do not add several time the same value to the array */
              for (i=0; i<ocount; i++)
                if ((*result)->items[i] == a)
                  break;
              if (i==ocount)
                {
                  *result = array_grow1(*result, ocount+1);
                  (*result)->items[ocount] = a;
                }
            }
          }
        /*else
          skip_subarray = true;*/
        break;
        
      default:  /* case VirtualTime */
        return false;  /* different virtual sources */
      }
    }
  /*else
    skip_subarray = is_compiletime(bsource);*/

  if (bcount == 0 && a->array == NullArray)
    return true;    /* shortcut */

#if COMPRESS_COMPILETIME_SUBITEMS
  if (/*skip_subarray*/ is_compiletime(bsource))
    {
      /* For compile-time values we don't bother comparing
         subarrays, because they only have a caching role
         in this case; they should never contain information
         different from what psyco_get_field() can load or
         reload from immutable data. */
#if PSYCO_DEBUG
      /* we just verify that there are only compile-time
         subitems. */
      int j;
      for (j=0; j<a->array->count; j++)
        extra_assert(a->array->items[j] == NULL ||
                     is_compiletime(a->array->items[j]->source));
#endif
      /* skip the subarray in the pseudo-code */
      skip_compatible_array(bcount);
      return true;
    }
#else   /* !COMPRESS_COMPILETIME_SUBITEMS */
  if (is_compiletime(bsource))
    {
      extra_assert(bcount == 0);
      return true;
    }
#endif  /* COMPRESS_COMPILETIME_SUBITEMS */

  return compatible_array(a->array, bcount, result, aref->array, recdepth+1);
}

/* The following function is the composition of fz_uncompress() and
   the above compatible_array(), optimized so that we need not build
   a whole uncompressed copy of the pseudo-code. */
static bool compatible_array(vinfo_array_t* aa, int count,
                             vinfo_array_t** result, vinfo_array_t* reference,
                             int recdepth)
{
  /* In the following comments, 'bb' refers to the implicit intermediate
     array that would be created by fz_uncompress(). */
  /* 'reference' is a either 'aa', or another array of items that already
     passed the test against the same pseudo-code. This lets us check
     shared structures. */

  /* special-case test. See comments below. */
#define CHECK_FOR_NULL(a)                                                       \
      if (a != NULL) {                                                          \
        /* if there is no proved progress, and 'a'                              \
           might just have been promoted,                                       \
           then we have to let compilation go on */                             \
        if (*result == NullArray &&                                             \
            is_compiletime(a->source) &&                                        \
            ((CompileTime_Get(a->source)->refcount1_flags & SkFlagFixed) != 0)) \
          return false;                                                         \
        /* if we are not too deep in the array, then we might as                \
           well try compiling with this extra information */                    \
        if (recdepth <= 2)                                                      \
          return false;                                                         \
      }

  int i;
  /* count = bb->count; */
  extra_assert(count >= 0);
  if (aa->count != count)
    {
      if (aa->count < count)   /* array too short; ok only if the extra items */
	{                      /*   in 'bb' are all NULL.                     */
	  do {
            if (fz_getopc() != FZ_OPC_NULL)
              return false;   /* differs */
          } while (aa->count < --count);
        }
      else  /* array too long */
        {
          /* the extra items in 'aa' must all be NULL. This is not strictly
             necessary for a compatibility (the above condition is more
             precise) but I guess that you get better results this way,
             because you have more information for a recompilation.
             XXX This assumption should be tested. */

          /* This potentially allows for unbounded array depth,
             so we disable it after a given depth and revert to the
             old behavior: all extra items are matched against b == NULL
             life below. */
          for (i=aa->count; i>count; )
            {
              vinfo_t* a = aa->items[--i];
              CHECK_FOR_NULL(a)
            }
        }
    }
  for (i=count; i--; )
    {
      int opc = fz_getopc();
      vinfo_t* a = aa->items[i];

      /* invariant */
      extra_assert(cmpinternal.tmp_counter <= cmpinternal.vcilink->time);

      if (opc == FZ_OPC_NULL)  /* 'b' is NULL */
        {
          /* if b == NULL, any value in 'a' is ok --
             with the exception of a fixed compile-time value, as
             created by a promotion. Without the following test,
             Psyco sometimes emits an infinite loop because the
             PsycoObject after promotion is found to be compatible
             with itself just before promotion. */
          CHECK_FOR_NULL(a)
        }
      else if (opc < 0)  /* 'b' is a link to another 'b'. */
        {
          /* We cannot compare right now the 'a' with the corresponding 'b'
             because we do not know it yet. We record the comparison as
             "to be done later" in the linked list. */
          if (a == NULL)
            return false;   /* shortcut: cannot match later */
          fz_pushstack(opc, a);
        }
      else      /* 'b' is a vinfo_t */
        {
          Source bsource = fz_getarg();

          /* Save the current position (resolving links require backtracking) */
          signed char* saved_buf_opc = cmpinternal.buf_opc;
          Source* saved_buf_args     = cmpinternal.buf_args;
          int saved_tmp_counter      = cmpinternal.tmp_counter;

          /* Compare 'a' and 'bsource'. */
          extra_assert(i < reference->count);
          if (!compatible_vinfo(a, bsource, opc, result, reference->items[i],
                                recdepth))
            return false;

          /* Only after the above call we know if any link previously pending
             link just resolved into the current 'b'. */
          if (cmpinternal.tmp_counter == cmpinternal.vcilink->time)
            {
              bool ok = true;
              struct vcilink_s* pending = NULL;  /* links that resolve to 'b' */
              struct vcilink_s* p;
              vinfo_t* preva;
              
              while (1) {
                /* Move all links with the current time to 'pending' */
                while (cmpinternal.tmp_counter == cmpinternal.vcilink->time)
                  {
                    p = cmpinternal.vcilink;
                    cmpinternal.vcilink = p->next;
                    p->next = pending;
                    pending = p;
                  }
                extra_assert(cmpinternal.tmp_counter<cmpinternal.vcilink->time);
                if (!pending)
                  break;   /* done */

                /* Resolve the next link */
              shortcut1:
                p = pending;
                pending = p->next;
                preva = p->v.preva;
                psyco_llfree_vci(p);

                /* First check if the same link is found later in the
                   linked list, and ignore it if so (optimization). */
                for (p = pending; p; p=p->next)
                  if (p->v.preva == preva)
                    goto shortcut1;

                if (ok && preva != a)
                  {
                    /* the two vinfo_ts shared in 'bb' are not shared in 'aa',
                       i.e. two nodes are shared in 'bb' but not in 'aa'.
                       We must compare the second node in 'aa' again with the
                       same single node of 'bb'. */
                    /* Backtracking */
#if ALL_CHECKS
                    signed char* buf_opc1 = cmpinternal.buf_opc;
                    Source* buf_args1     = cmpinternal.buf_args;
                    int tmp_counter1      = cmpinternal.tmp_counter;
#endif
                    cmpinternal.tmp_counter = saved_tmp_counter;
                    cmpinternal.buf_args    = saved_buf_args;
                    cmpinternal.buf_opc     = saved_buf_opc;
                    ok = compatible_vinfo(preva, bsource, opc, result, a,
                                          recdepth);
#if ALL_CHECKS
                    if (ok) {
                      extra_assert(buf_opc1     == cmpinternal.buf_opc);
                      extra_assert(buf_args1    == cmpinternal.buf_args);
                      extra_assert(tmp_counter1 == cmpinternal.tmp_counter);
                    }
#endif
                  }

                /* go on with the loop even if !ok, to free all items left
                   in [pbegin, pend[. They must be freed now because they are
                   no longer members of the main linked list --
                   the members of the linked list are freed automatically by
                   fz_compatible_array() */
              }

              if (!ok)
                return false;
            }
          
          cmpinternal.tmp_counter++;
          extra_assert(cmpinternal.tmp_counter <= cmpinternal.vcilink->time);
        }
    }
  return true;
#undef CHECK_FOR_NULL
}

#if COMPRESS_COMPILETIME_SUBITEMS
/* same as 'compatible_array', faster, for when you are not
   interested in the result */
static void skip_compatible_array(int count)
{
  int i;
  extra_assert(count >= 0);
  for (i=count; i--; )
    {
      int opc = fz_getopc();
      extra_assert(cmpinternal.tmp_counter <= cmpinternal.vcilink->time);
      if (opc == FZ_OPC_NULL)
        ;
      else if (opc < 0)
        ;
      else
        {
#if PSYCO_DEBUG
          Source bsource = fz_getarg();
          extra_assert(is_compiletime(bsource));
#else
          fz_getarg();
#endif
          skip_compatible_array(opc);

          /* no link should resolve now, fz_compress() takes care of that */
          extra_assert(cmpinternal.tmp_counter < cmpinternal.vcilink->time);
          cmpinternal.tmp_counter++;
        }
    }
}
#endif  /* COMPRESS_COMPILETIME_SUBITEMS */

PSY_INLINE bool fz_compatible_array(vinfo_array_t* aa, FrozenPsycoObject* fpo,
                                vcompatible_t* result) {
  bool ok;
  fz_load_fpo_stack(fpo);
  ok = compatible_array(aa, fz_getopc(), &result->diff, aa, 0);
  
  /* free the linked list (it should already be free if 'ok') */
  while (cmpinternal.vcilink != &cmpinternal.sentinel)
    {
      struct vcilink_s* p = cmpinternal.vcilink;
      cmpinternal.vcilink = p->next;
      psyco_llfree_vci(p);
    }
  
  return ok;
}


#endif /* VLOCALS_OPC */


DEFINEFN
void psyco_delete_unused_vars(PsycoObject* po, global_entries_t* ge)
{
  int i, limit;
  PyObject* plist = ge->fatlist;
  extra_assert(PyList_Check(plist));
  limit = PyList_GET_SIZE(plist);
  for (i=0; i<limit; i++)
    {
      int num;
      vinfo_t* vi;
      PyObject* o1 = PyList_GET_ITEM(plist, i);
      if (!PyInt_Check(o1))
        break;
      num = PyInt_AS_LONG(o1);
      /* delete variable 'num' (it might already be unset) */
      /* note that if psyco_delete_unused_vars() is called by
         psyco_compile_code(), before any buffer is allocated,
         it may not emit any code. */
      vi = LOC_LOCALS_PLUS[num];
      LOC_LOCALS_PLUS[num] = Psyco_SafelyDeleteVar(po, vi);
      vinfo_decref(vi, po);
    }
}

DEFINEFN
vcompatible_t* psyco_compatible(PsycoObject* po, global_entries_t* patterns)
{
  static vcompatible_t result;  /* argh, a global variable -- well, the rest of
                                   the implementation is not re-entrent anyway */
  vinfo_array_t* bestresult = NULL;   /* best result so far */
  CodeBufferObject* bestbuf = NULL;
  int i;
  PyObject* plist = patterns->fatlist;
  extra_assert(PyList_Check(plist));
  i = PyList_GET_SIZE(plist);
  while (i--)    /* the most dummy algorithm: step by step in the list, */
    {            /* checking for a match at each step.                  */
      CodeBufferObject* codebuf;
      PyObject* o1 = PyList_GET_ITEM(plist, i);
      if (!CodeBuffer_Check(o1))
        break;
      codebuf = (CodeBufferObject*) o1;
      result.matching = codebuf;
      result.diff = NullArray;
      extra_assert(CodeBuffer_Check(codebuf));
      fz_check_invariant(&codebuf->snapshot);
      if (fz_compatible_array(&po->vlocals, &codebuf->snapshot, &result))
	{
          /* compatible_array() leaves data in the 'tmp' fields.
             It must be cleared unless it is the final result of
             psyco_compatible() itself. */
	  if (result.diff == NullArray)
	    {
              /* Total match */
              if (bestresult != NULL)
                array_release(bestresult);
              return &result;
	    }
          else
            {
              /* Partial match, clear 'tmp' fields */
              fz_restore_invariant(&codebuf->snapshot);
              if (bestresult != NULL)
                {
                  if (bestresult->count <= result.diff->count)
                    {
                      array_release(result.diff);
                      continue;  /* not better than the previous partial match */
                    }
                  array_release(bestresult);
                }
              /* Record the best partial match we found so far */
              bestresult = result.diff;
              bestbuf    = codebuf;
            }
	}
      else   /* compatible_array() should have reset all 'tmp' fields */
        fz_check_invariant(&codebuf->snapshot);
    }
  if (bestresult == NULL)
    return NULL;
  else
    {
      result.matching = bestbuf;
      result.diff     = bestresult;
      return &result;
    }
}

DEFINEFN
void psyco_stabilize(vcompatible_t* lastmatch)
{
  if (lastmatch->diff == NullArray)
    fz_restore_invariant(&lastmatch->matching->snapshot);
  else
    fz_check_invariant(&lastmatch->matching->snapshot);
  array_release(lastmatch->diff);
}


 /***************************************************************/
/***                         Unification                       ***/
 /***************************************************************/


/* psyco_unify() is implemented in idispatcher.c */


DEFINEFN
CodeBufferObject* psyco_unify_code(PsycoObject* po, vcompatible_t* lastmatch)
{
  /* simplified interface to psyco_unify() without using a previously
     existing code buffer. */

  CodeBufferObject* target;
  code_t localbuf[GUARANTEED_MINIMUM];
  /* relies on the fact that psyco_unify() has no room at all in localbuf.
     Anything but the final JMP will trigger the creation of a new code
     buffer. */
  po->code = localbuf;
  INIT_CODE_EMISSION(po->code);
  po->codelimit = NULL;
  psyco_unify(po, lastmatch, &target);
  return target;
}

#define KEEP_MARK   ((vinfo_t*) 1)

static int mark_to_keep(vinfo_array_t* array, bool virtual_parent)
{
  int i, total=0;
  for (i=array->count; i--; )
    {
      vinfo_t* vi = array->items[i];
      if (vi != NULL)
        {
          if (is_runtime(vi->source) && vi->tmp == NULL)
            {
              if (!virtual_parent)
                continue;
              /* mark this item to be kept */
              vi->tmp = KEEP_MARK;
              total++;
            }
          if (vi->array != NullArray)
            total += mark_to_keep(vi->array, is_virtualtime(vi->source));
        }
    }
  return total;
}

static void remove_non_marked(vinfo_array_t* array, PsycoObject* po)
{
  int i;
  for (i=array->count; i--; )
    {
      vinfo_t* vi = array->items[i];
      if (vi != NULL)
        {
          if (is_runtime(vi->source) && vi->tmp == NULL)
            {
              /* remove this item */
              array->items[i] = NULL;
              vinfo_decref(vi, po);
            }
          else if (vi->array != NullArray)
            {
              if (is_compiletime(vi->source))
                {
                  /* remove all sub-items */
                  vinfo_array_t* array = vi->array;
#if PSYCO_DEBUG
                  /* we just verify that there are only compile-time
                     subitems. */
                  int j;
                  for (j=0; j<array->count; j++)
                    extra_assert(array->items[j] == NULL ||
                                 is_compiletime(array->items[j]->source));
#endif
                  vi->array = NullArray;
                  array_delete(array, po);
                }
              else
                remove_non_marked(vi->array, po);
            }
        }
    }
}

DEFINEFN
int psyco_simplify_array(vinfo_array_t* array, PsycoObject* po)
{
  /* We remove a run-time vinfo_t if it is not directly in 'array' and
     if it is not in the sub-vinfo_array_t of any virtual-time source. */
  
  /* First mark with a non-NULL value all run-time sources that must
     be kept. */
  int total;
  assert_cleared_tmp_marks(array);
  total = mark_to_keep(array, true);

  /* Remove all non-marked run-time sources */
  remove_non_marked(array, po);

  /* Done */
  return total;
}

static void remove_non_compiletime(vinfo_t* v, PsycoObject* po)
{
  vinfo_array_t* array = v->array;
  int j, length=array->count, newlength=0;
  for (j=0; j<length; j++)
    {
      vinfo_t* vi = array->items[j];
      if (vi != NULL)
        {
          if (!is_compiletime(vi->source))
            {
              array->items[j] = NULL;
              vinfo_decref(vi, po);
            }
          else
            newlength = j+1;
        }
    }
  vinfo_array_shrink(po, v, newlength);
}


 /***************************************************************/
/***                Promotion and un-promotion                 ***/
 /***************************************************************/


/*****************************************************************/
 /***   Promotion of a run-time variable into a fixed           ***/
  /***   compile-time one                                        ***/


/* Implementation tactics */

/* 0 -- use a plain Python dictionary whose keys
        are the value to promote and values the code objects.
   1 -- put code buffers in a chained list,
        with the most used items moving forward in the list.
   2 -- order the code buffers as a binary search tree,
        with the most used nodes moving up in the tree (not implemented)
*/
#define PROMOTION_TACTIC             1


#if PROMOTION_TACTIC == 1
typedef struct rt_local_buf_s {
# if CODE_DUMP
  long signature;
# endif
  struct rt_local_buf_s* next;
  long key;
} rt_local_buf_t;
#endif

typedef struct { /* produced at compile time and read by the dispatcher */
  INTERNAL_PROMOTION_FIELDS
  
  PsycoObject* po;        /* state before promotion */
  vinfo_t* fix;           /* variable to promote */
  
#if PROMOTION_TACTIC == 0
  PyObject* spec_dict;    /* local cache (promotions to already-seen values) */
# if CODE_DUMP
  void** chained_list;    /* must be last, with spec_dict just before */
# endif
#endif

#if PROMOTION_TACTIC == 1
  rt_local_buf_t* local_chained_list;
# if CODE_DUMP
  long zero_tag;
# endif
#endif
} rt_promotion_t;


/* this macro might be redefined below */
#define QUICK_LOOKUP_PROMOTION_VALUE(fs, value, result)         \
                result = lookup_old_promotion_values(fs, value)


#if PROMOTION_TACTIC == 0
#define NEED_PYOBJ_KEY
PSY_INLINE code_t* lookup_old_promotion_values(rt_promotion_t* fs,
                                           PyObject* key)
{
  /* have we already seen this value? */
  CodeBufferObject* codebuf;
  codebuf = (CodeBufferObject*) PyDict_GetItem(fs->spec_dict, key);
  if (codebuf != NULL)   /* yes */
    return (code_t*) codebuf->codestart;
  return NULL;  /* no */
}
#endif  /* PROMOTION_TACTIC == 0 */

#if PROMOTION_TACTIC == 1
#  if PROMOTION_FAST_COMMON_CASE
static
#  else
PSY_INLINE
#  endif
code_t* lookup_old_promotion_values(rt_promotion_t* fs, long value)
{
  rt_local_buf_t** ppbuf;
  if (fs->local_chained_list == NULL)
    return NULL;  /* not found (list is empty) */

#if PROMOTION_FAST_COMMON_CASE
  /* 'fs->local_chained_list' points to the current head
     of the list, which we know is not what we are looking
     for because otherwise the CMP/JE instructions
     would have found it and we would not be here */
  extra_assert(fs->local_chained_list->key != value);
#else
  if (fs->local_chained_list->key == value)
    return (code_t*)(fs->local_chained_list+1);  /* it is the head of the list */
#endif

  ppbuf = &fs->local_chained_list->next;
  while (1)
    {
      rt_local_buf_t* buf = *ppbuf;
      if (buf == NULL)
        return NULL;  /* not found (list exhausted) */
      if (buf->key == value)
        {
          /* found inside the list, put it at the head */
          *ppbuf = buf->next;
          buf->next = fs->local_chained_list;
          fs->local_chained_list = buf;
          return (code_t*)(buf+1);
        }
      ppbuf = &buf->next;
    }
}

#if PROMOTION_FAST_COMMON_CASE
static int quick_lookup_counter = 0;
#  undef QUICK_LOOKUP_PROMOTION_VALUE
#  define QUICK_LOOKUP_PROMOTION_VALUE(fs, value, res)   do {   \
        rt_local_buf_t* buf = (fs)->local_chained_list;         \
        if (buf == NULL) {                                      \
          res = NULL;  /* not found (list is empty) */          \
        }                                                       \
        else if ((quick_lookup_counter-=13) >= 0) {             \
          for (buf=buf->next; buf!=NULL; buf=buf->next) {       \
            if (buf->key == (value))                            \
              return (code_t*)(buf+1);                          \
          }                                                     \
          res = NULL;  /* not found */                          \
        }                                                       \
        else {                                                  \
          /* approximately once every 23 times, go through */   \
          /* the slower path that will move the item to    */   \
          /* the head of the search list if it is found.   */   \
          quick_lookup_counter += 307;                          \
          res = lookup_old_promotion_values(fs, value);         \
        }                                                       \
      } while (0)
#endif

PSY_INLINE int lookup_count_previous_values(rt_promotion_t* fs,
					    rt_local_buf_t** megabuf)
{
	int result = 0;
	rt_local_buf_t* buf = fs->local_chained_list;
	while (buf) {
		if (buf->key == -1)   /* use (PyObject*)(-1) as a marker */
			*megabuf = buf;
		result++;
		buf = buf->next;
	}
	return result;
}
#endif  /* PROMOTION_TACTIC == 1 */


static code_t* do_promotion_internal(rt_promotion_t* fs,
#ifdef NEED_PYOBJ_KEY
                                     PyObject* key,
#else
                                     long key,
#endif
                                     source_known_t* sk)
{
  CodeBufferObject* codebuf;
  code_t* result;
  vinfo_t* v;
  PsycoObject* newpo;
  PsycoObject* po = fs->po;
  mergepoint_t* mp;

  /* get a copy of the compiler state */
  newpo = PsycoObject_Duplicate(po);
  if (newpo == NULL)
    OUT_OF_MEMORY();
  /* store the copy back into 'fs' and use the old 'po' to compile.
     We do so because in 'newpo' all 'tmp' fields are now NULL,
     but no longer in 'po'. */
  fs->po = newpo;
  v = fs->fix;      /* get the variable we will promote to compile-time... */
  fs->fix = v->tmp; /*     ...and update 'fs' with its copy in 'newpo'     */
  
  /* fix the value of 'v' */
  CHKTIME(v->source, RunTime);   /* from run-time to compile-time */
#if REG_TOTAL > 0
  if (!RSOURCE_REG_IS_NONE(v->source))
    {
      /* remove this value from 'po->regarray' */
      REG_NUMBER(po, RSOURCE_REG(v->source)) = NULL;
      SET_RUNTIME_REG_TO_NONE(v);
    }
#endif
  v->source = CompileTime_NewSk(sk);
  /* compile from this new state, in which 'v' has been promoted to
     compile-time. */
  mp = psyco_exact_merge_point(po->pr.merge_points, po->pr.next_instr);

#if PROMOTION_TACTIC == 0
  codebuf = psyco_compile_code(po, mp);

  /* store the new code buffer into the local cache */
  RECLIMIT_SAFE_ENTER();
  if (PyDict_SetItem(fs->spec_dict, key, (PyObject*) codebuf))
    OUT_OF_MEMORY();
  RECLIMIT_SAFE_LEAVE();
  Py_DECREF(codebuf);  /* there is a reference left
                          in the dictionary */
  result = (code_t*) codebuf->codestart;
#endif

#if PROMOTION_TACTIC == 1
  codebuf = psyco_new_code_buffer(NULL, NULL, &po->codelimit);
  {
    code_t* codeend;
    rt_local_buf_t* buf = (rt_local_buf_t*) codebuf->codestart;
    code_t* code = (code_t*)(buf+1);
    ALIGN_NO_FILL();
    result = code;
    buf = ((rt_local_buf_t*) code) - 1;
    
# if CODE_DUMP
    memset(codebuf->codestart, 0xCC, ((char*) buf) - ((char*) codebuf->codestart));
    buf->signature = 0x66666666;
# endif
    buf->next = fs->local_chained_list;
    buf->key = key;
    fs->local_chained_list = buf;
    
    po->code = insn_code_label(result);
    codeend = psyco_compile(po, mp, false);
    psyco_shrink_code_buffer(codebuf, codeend);
    /* XXX don't know what to do with reference to 'codebuf' */
  }
#endif

  dump_code_buffers();
  return result;
}

static code_t* detected_megamorphic_pyobj_site(rt_promotion_t* fs)
{
  CodeBufferObject* codebuf;
  code_t* result;
  vinfo_t* v;
  PsycoObject* newpo;
  PsycoObject* po = fs->po;
  mergepoint_t* mp;

  /* get a copy of the compiler state */
  newpo = PsycoObject_Duplicate(po);
  if (newpo == NULL)
    OUT_OF_MEMORY();
  /* store the copy back into 'fs' and use the old 'po' to compile.
     We do so because in 'newpo' all 'tmp' fields are now NULL,
     but no longer in 'po'. */
  fs->po = newpo;
  v = fs->fix;      /* get the variable we will mark as megamorphic... */
  fs->fix = v->tmp; /*     ...and update 'fs' with its copy in 'newpo'     */
  
  /* mark 'v' as megamorphic */
  CHKTIME(v->source, RunTime);
  v->source |= RunTime_Megamorphic;
  /* compile from this new state, in which 'v' has been flagged */
  mp = psyco_exact_merge_point(po->pr.merge_points, po->pr.next_instr);

#if PROMOTION_TACTIC == 0
#  error "XXX reimplement"
#endif

#if PROMOTION_TACTIC == 1
  codebuf = psyco_new_code_buffer(NULL, NULL, &po->codelimit);
  {
    code_t* codeend;
    rt_local_buf_t* buf = (rt_local_buf_t*) codebuf->codestart;
    code_t* code = (code_t*)(buf+1);
    ALIGN_NO_FILL();
    result = code;
    buf = ((rt_local_buf_t*) code) - 1;
    
# if CODE_DUMP
    memset(codebuf->codestart, 0xCC, ((char*) buf) - ((char*) codebuf->codestart));
    buf->signature = 0x66666666;
# endif
    buf->next = fs->local_chained_list;
    buf->key = -1;   /* use (PyObject*)(-1) as a marker */
    fs->local_chained_list = buf;
    
    po->code = insn_code_label(result);
    codeend = psyco_compile(po, mp, false);
    psyco_shrink_code_buffer(codebuf, codeend);
    /* XXX don't know what to do with reference to 'codebuf' */
  }
#endif

  dump_code_buffers();
  return result;
}


/* NOTE: the following two functions must be as fast as possible, because
   they are called from the run-time code even during normal (non-compiling)
   execution. */
static code_t* do_promotion_long(rt_promotion_t* fs, long value)
{
  /* need a PyObject* key for the local cache dictionary */
  code_t* result;

#ifdef NEED_PYOBJ_KEY
  PyObject* key1 = PyInt_FromLong(value);
  if (key1 == NULL)
    OUT_OF_MEMORY();
#else
  long key1 = value;
#endif

  /* have we already seen this value? */
  QUICK_LOOKUP_PROMOTION_VALUE(fs, key1, result);
  if (result == NULL)
    {
      /* no -> we must build new code */
      result = do_promotion_internal(fs, key1, sk_new(value, SkFlagFixed));
    }
#ifdef NEED_PYOBJ_KEY
  Py_DECREF(key1);
#endif
  /* done -> jump to the codebuf */
  return fix_fast_common_case(fs, value, result);
}

static code_t* do_promotion_pyobj(rt_promotion_t* fs, PyObject* key)
{
  code_t* result;

#ifdef NEED_PYOBJ_KEY
  PyObject* key1 = key;
#else
  long key1 = (long) key;
#endif

  /* have we already seen this value? */
  QUICK_LOOKUP_PROMOTION_VALUE(fs, key1, result);
  if (result == NULL)
    {
      /* no -> we must build new code */
      Py_INCREF(key);
      result = do_promotion_internal(fs, key1, sk_new((long) key,
                                                      SkFlagFixed|SkFlagPyObj));
    }
  /* done -> jump to the codebuf */
  return fix_fast_common_case(fs, (long) key, result);
}

static code_t* do_promotion_pyobj_mega(rt_promotion_t* fs, PyObject* key)
{
  code_t* result;

#ifdef NEED_PYOBJ_KEY
  PyObject* key1 = key;
#else
  long key1 = (long) key;
#endif

  /* have we already seen this value? */
  QUICK_LOOKUP_PROMOTION_VALUE(fs, key1, result);
  if (result == NULL)
    {
      /* no -> did we already promote many objects here? */
      rt_local_buf_t* megabuf = NULL;
      if (lookup_count_previous_values(fs, &megabuf) >= MEGAMORPHIC_MAX)
        {
          /* yes -> stop specializing */
          if (megabuf == NULL)
            return detected_megamorphic_pyobj_site(fs);
          else
            return (code_t*)(megabuf+1);  /* mega version already compiled */
        }
      /* no -> we must build new code */
      Py_INCREF(key);
      result = do_promotion_internal(fs, key1, sk_new((long) key,
                                                      SkFlagFixed|SkFlagPyObj));
    }
  /* done -> jump to the codebuf */
  return fix_fast_common_case(fs, (long) key, result);
}

DEFINEFN
code_t* psyco_finish_promotion(PsycoObject* po, vinfo_t* fix, int pflags)
{
  rt_promotion_t* fs;
  void* do_promotion;

  /* we remove the non-compile-time array values from 'fix' */
  if (fix->array != NullArray)
    remove_non_compiletime(fix, po);
  
  TRACE_EXECUTION("PROMOTION");

  /* write the code that calls the proxy 'do_promotion' */
  switch (pflags) {
  case 0:
    do_promotion = &do_promotion_long;
    break;
  case PFlagPyObj:
    do_promotion = &do_promotion_pyobj;
    break;
  /*case PFlagMegamorphic: ... */
  case PFlagPyObj | PFlagMegamorphic:
    do_promotion = &do_promotion_pyobj_mega;
    break;
  default:
    psyco_fatal_msg("bad pflags");
    return NULL;
  }
  fs = (rt_promotion_t*) ipromotion_finish(po, fix, do_promotion);

  /* fill in the constant structure that 'do_promotion' will get as parameter */
  clear_tmp_marks(&po->vlocals);
  psyco_assert_coherent(po);
  fs->po = po;    /* don't release 'po' */
  fs->fix = fix;
  
#if PROMOTION_TACTIC == 0
  fs->spec_dict = PyDict_New();
  if (fs->spec_dict == NULL)
    OUT_OF_MEMORY();
# if CODE_DUMP
  fs->chained_list = psyco_codebuf_spec_dict_list;
  psyco_codebuf_spec_dict_list = (void**)&fs->chained_list;
# endif
#endif

#if PROMOTION_TACTIC == 1
  fs->local_chained_list = NULL;
# if CODE_DUMP
  fs->zero_tag = 0;
# endif
#endif
  
  return (code_t*)(fs+1);  /* end of code == end of 'fs' structure */
}


/*****************************************************************/
 /***   Promotion of certain run-time values into               ***/
  /***   compile-time ones (promotion only occurs for certain    ***/
   /***   values, e.g. for types that we know how to optimize).   ***/

#if USE_RUNTIME_SWITCHES

typedef struct { /* produced at compile time and read by the dispatcher */
  fixed_switch_t* rts;    /* special values */
  PsycoObject* po;        /* state before promotion */
  vinfo_t* fix;           /* variable to promote */
  long kflags;            /* flags after promotion */
  code_t* switchcodeend;  /* end of the private copy of the switch code */
} rt_fixed_switch_t;

static code_t* do_fixed_switch(rt_fixed_switch_t* rtfxs, long value)
{
  int item;
  CodeBufferObject* codebuf;
  fixed_switch_t* rts = rtfxs->rts;
  vinfo_t* v;
  PsycoObject* newpo;
  PsycoObject* po = rtfxs->po;

  /* get a copy of the compiler state */
  newpo = psyco_duplicate(po);
  /* store the copy back into rtfxs and use the old 'po' to compile.
     We do so because in 'newpo' all 'tmp' fields are now NULL,
     but no longer in 'po'. */
  rtfxs->po = newpo;
  v = rtfxs->fix;      /* get the variable we will promote to compile-time... */
  rtfxs->fix = v->tmp; /*   ...and update 'rtfxs' with its copy in 'newpo'    */

  item = psyco_switch_lookup(rts, value);   /* which value did we found? */
  if (item == -1)
    {
      /* none --> go into 'default' mode */
      /* abuse the 'array' field to point to this fixed_switch_t
         to mean 'known to be none of the special values'.
         See known_to_be_default(). */
      v->array = NullArrayAt(rts->zero);
    }
  else
    {
      /* fix the value of 'v' to the one we found */
      CHKTIME(v->source, RunTime);   /* from run-time to compile-time */
      if (!RUNTIME_REG_IS_NONE(v))
        REG_NUMBER(po, RUNTIME_REG(v)) = NULL;
      v->source = CompileTime_NewSk(sk_new(value, rtfxs->kflags));
    }

  /* compile from this new state */
  codebuf = psyco_compile_code(po,  psyco_exact_merge_point(po->pr.merge_points,
                                                            po->pr.next_instr));

  /* store the pointer to the new code directly into
     the original code that jumped to do_fixed_switch() */
  psyco_fix_switch_case(rts, rtfxs->switchcodeend, item, codebuf->codeptr);
  
  return codebuf->codeptr;  /* jump there */
  /* XXX no place to store the reference to codebuf */
}

DEFINEFN
code_t* psyco_finish_fixed_switch(PsycoObject* po, vinfo_t* fix, long kflags,
                                  fixed_switch_t* special_values)
{
  rt_fixed_switch_t* rtfxs;
  code_t* switchcodeend;
  CHKTIME(fix->source, RunTime);
  extra_assert(fix->array->count == 0);  /* cannot fix array values,
                                            because of known_to_be_default() */
  TRACE_EXECUTION("FIXED_SWITCH");
  BEGIN_CODE
  NEED_CC();
  RTVINFO_IN_REG(fix);
  switchcodeend = code = psyco_write_run_time_switch(special_values, code,
                                                     RUNTIME_REG(fix));
  
  TEMP_SAVE_REGS_FN_CALLS;   /* save all registers that might be clobbered */
  CALL_SET_ARG_FROM_RT(fix->source, 1, 2);/* argument index 1 out of total 2 */
  END_CODE

  /* write the code that calls the proxy 'do_fixed_switch' */
  rtfxs = (rt_fixed_switch_t*) psyco_jump_proxy(po, &do_fixed_switch, 1, 2);

  /* fill in the constant struct that 'do_fixed_switch' will get as parameter */
  clear_tmp_marks(&po->vlocals);
  psyco_assert_coherent(po);
  rtfxs->rts = special_values;
  rtfxs->po = po;
  rtfxs->fix = fix;
  rtfxs->kflags = kflags;
  rtfxs->switchcodeend = switchcodeend;
  return (code_t*)(rtfxs+1);
}

#endif   /* USE_RUNTIME_SWITCHES */


/*****************************************************************/
 /***   Un-Promotion from non-fixed compile-time into run-time  ***/

static void array_remove_vinfo(vinfo_array_t* array, vinfo_t* vi)
{
  int i = array->count;
  while (i--)
    {
      vinfo_t* a = array->items[i];
      if (a != NULL)
        {
          if (a == vi)
            {
              extra_assert(a->refcount > 1);
              vinfo_decref(a, NULL);  /* other references expected */
              array->items[i] = NULL;
            }
          else if (a->array != NullArray)
            array_remove_vinfo(a->array, vi);
        }
    }
}

static void array_remove_inside_ct(vinfo_array_t* array, vinfo_t* vi)
{
  int i = array->count;
  while (i--)
    {
      vinfo_t* a = array->items[i];
      if (a != NULL && a->array != NullArray)
        {
          if (is_compiletime(a->source))
            array_remove_vinfo(a->array, vi);
          else
            array_remove_inside_ct(a->array, vi);
        }
    }
}

DEFINEFN
void psyco_unfix(PsycoObject* po, vinfo_t* vi)
{
  /* Convert 'vi' from compile-time to run-time variable. */
  vinfo_t* newvi;
  source_known_t* sk;
  CHKTIME(vi->source, CompileTime);

  /*printf("psyco_unfix(%p, %p, %p)\n", po, po->code, vi);*/

  /* forget all sub-items of the compile-time 'vi',
     which should all be compile-time */
  if (vi->array != NullArray)
    {
      array_delete(vi->array, po);
      vi->array = NullArray;
    }

  /* A particular case that *do* occur:
     'vi' was always selected as a compile-time vinfo_t not within
     another compile-time vinfo_t's subarray; but it could
     actually appear more than once in po->vlocals, and another
     occurrence could be inside another compile-time vinfo_t.
     As compile-time vinfo_ts are not allowed to contain anything
     but compile-time vinfo_ts, unfixing 'vi' would break it.
     In this situation we remove the faulty occurrences. */
  if (vi->refcount > 1)
    array_remove_inside_ct(&po->vlocals, vi);
  assert_array_contains_nonct(&po->vlocals, vi);

  newvi = make_runtime_copy(po, vi);
  /* make_runtime_copy() never fails for compile-time sources */
  extra_assert(newvi != NULL);

  /* release 'vi->source' and move 'newvi->source' into it */
  sk = CompileTime_Get(vi->source);
  if (sk->refcount1_flags & SkFlagPyObj) {
    /* XXX can't release the PyObject anywhere, because we
       write a pointer to it in the code itself. We should
       somehow transfer the ownership of this reference to
       the CodeBufferObject. Fix me when implementing
       memory releasing! */
    sk->refcount1_flags &= ~SkFlagPyObj;
  }
  sk_decref(sk);
  vinfo_move(po, vi, newvi);
}
