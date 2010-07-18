#include "codemanager.h"
#include <ipyencoding.h>
#include "platform.h"

/*** Allocators for Large Executable Blocks of Memory ***/

#define BUFFER_SIGNATURE    0xE673B506   /* arbitrary */

typedef struct codemanager_buf_s {
  long signature;
  char* position;
  bool inuse;
  struct codemanager_buf_s* next;
} codemanager_buf_t;

static codemanager_buf_t* big_buffers = NULL;
static codemanager_buf_t* completed_big_buffers = NULL;


PSY_INLINE void check_signature(codemanager_buf_t* b)
{
  if (b->signature != BUFFER_SIGNATURE)
    Py_FatalError("psyco: code buffer overwrite detected");
}

static void allocate_more_buffers(codemanager_buf_t** bb)
{
  static char plat_ok = 0;
  char* p;
  long allocated;
  int num_bigblocks = 0;

  if (plat_ok != 'n')
    {
      /* try the platform-specific allocator */
      allocated = psyco_allocate_executable_buffer(BIG_BUFFER_SIZE, &p);
      num_bigblocks = allocated / BIG_BUFFER_SIZE;
      if (num_bigblocks <= 0)
        {
          /* failed */
          if (plat_ok == 0)
            plat_ok = 'n';   /* doesn't work, don't try again */
          else
            OUT_OF_MEMORY();
        }
      else
        plat_ok = 'y';   /* works */
    }
  if (num_bigblocks <= 0)
    {
      p = (char*) PyMem_MALLOC(BIG_BUFFER_SIZE);
      if (p == NULL)
        OUT_OF_MEMORY();
      num_bigblocks = 1;
    }
  while (--num_bigblocks >= 0)
    {
      /* the codemanager_buf_t structure is put at the end of the buffer,
         with its signature to detect overflows (just in case) */
#define BUFFER_START_OFFSET  (BIG_BUFFER_SIZE - sizeof(codemanager_buf_t))
      codemanager_buf_t* b;
      b = (codemanager_buf_t*) (p + BUFFER_START_OFFSET);
      b->signature = BUFFER_SIGNATURE;
      b->position = p;
      b->next = NULL;
      /* insert 'b' at the end of the chained list */
      *bb = b;
      bb = &b->next;
      p += BIG_BUFFER_SIZE;
    }
}

static code_t* get_next_buffer(code_t** limit)
{
  codemanager_buf_t* b;
  codemanager_buf_t** bb;
  for (b=big_buffers; b!=NULL; b=b->next)
    {
      check_signature(b);
      if (!b->inuse)
        break;  /* returns the first (oldest) unlocked buffer */
    }
  
  if (b == NULL)
    {
      /* no more free buffers, allocate one or a few new ones */
      for (bb=&big_buffers; *bb!=NULL; bb=&(*bb)->next)
        ;
      allocate_more_buffers(bb);
      b = *bb;
    }
  b->inuse = true;
  *limit = ((code_t*) b) - GUARANTEED_MINIMUM;
  return (code_t*) b->position;
}

DEFINEFN int psyco_locked_buffers(void)
{
  codemanager_buf_t* b;
  int count = 0;
  for (b=big_buffers; b!=NULL; b=b->next)
    if (b->inuse)
      count++;
  return count;
}

static void close_buffer_use(code_t* code)
{
  codemanager_buf_t* b;
  for (b=big_buffers; b!=NULL; b=b->next)
    {
      check_signature(b);
      if (b->position <= (char*) code && (char*) code <= (char*) b)
        {
          extra_assert(b->inuse);
          ALIGN_NO_FILL();
          /* unlock the buffer */
          psyco_memory_usage += (char*) code - b->position;
          b->position = (char*) code;
          b->inuse = false;
          
          if (code > ((code_t*) b) - (BUFFER_MARGIN+2*GUARANTEED_MINIMUM))
            {
              /* buffer nearly full, remove it from the chained list */
              codemanager_buf_t** bb;
              for (bb=&big_buffers; *bb!=b; bb=&(*bb)->next)
                ;
              *bb = b->next;
              /* add it to the list of completed buffers */
              b->next = completed_big_buffers;
              completed_big_buffers = b;
            }
          return;
        }
    }
  Py_FatalError("psyco: code buffer allocator corruption");
}


static CodeBufferObject* new_code_buffer(PsycoObject* po, global_entries_t* ge,
                                         code_t* proxy_to, code_t** plimit)
{
  CodeBufferObject* b;
  code_t* limit;
  psyco_trash_object(NULL);
  if (plimit == NULL)
    plimit = &limit;

  b = PyObject_New(CodeBufferObject, &CodeBuffer_Type);
  if (b == NULL)
    OUT_OF_MEMORY();
  if (proxy_to != NULL)
    {
      *plimit = NULL;
      b->codestart = proxy_to;  /* points inside another code buffer */
      SET_CODEMODE(b, "proxy");
    }
  else
    {
      /* start a new code buffer */
      b->codestart = get_next_buffer(plimit);
      SET_CODEMODE(b, "(compiling)");
    }
  debug_printf(3, ("%s code buffer %p\n",
                   proxy_to==NULL ? "new" : "proxy", b->codestart));
  
  fpo_mark_new(&b->snapshot);
  if (po == NULL)
    fpo_mark_unused(&b->snapshot);
  else
    {
      if (is_respawning(po))
        Py_FatalError("psyco: internal bug: respawning in new_code_buffer()");
      fpo_build(&b->snapshot, po);
      if (ge != NULL)
        register_codebuf(ge, b);
      po->respawn_cnt = 0;
      po->respawn_proxy = b;
    }
  return b;
}

DEFINEFN
CodeBufferObject* psyco_new_code_buffer(PsycoObject* po, global_entries_t* ge, code_t** plimit)
{
  return new_code_buffer(po, ge, NULL, plimit);
}

DEFINEFN
CodeBufferObject* psyco_proxy_code_buffer(PsycoObject* po, global_entries_t* ge)
{
  return new_code_buffer(po, ge, po->code, NULL);
}

#if 0    /* not used any more */
DEFINEFN
CodeBufferObject* psyco_minimal_code_buffer(code_t* code)
{
  return new_code_buffer(NULL, NULL, code, NULL);
}
#endif

#if 0    /* not used in this version */
DEFINEFN
CodeBufferObject* psyco_new_code_buffer_size(int size)
{
  PyObject* o;
  CodeBufferObject* b;
  
  /* PyObject_New is inlined */
  o = PyObject_MALLOC(sizeof(CodeBufferObject) + size);
  if (o == NULL)
    return (CodeBufferObject*) PyErr_NoMemory();
  b = (CodeBufferObject*) PyObject_INIT(o, &CodeBuffer_Type);
  b->codestart = (code_t*) (b + 1);
  b->po = NULL;
  debug_printf(3, ("new_code_buffer_size(%d) %p\n", size, b->codestart));
  return b;
}
#endif

#if CODE_DUMP
DEFINEVAR CodeBufferObject* psyco_codebuf_chained_list = NULL;
DEFINEVAR void** psyco_codebuf_spec_dict_list = NULL;
#endif

DEFINEFN
void psyco_shrink_code_buffer(CodeBufferObject* obj, code_t* codeend)
{
  /* Note: "disassemble" will give a wrong size estimation if the buffer has
     been split by END_CODE (which occurs very rarely) */
  debug_printf(3, ("disassemble %p %p    (%d bytes)\n", obj->codestart,
                   codeend, codeend - ((code_t*)obj->codestart)));
  if (VERBOSE_LEVEL == 2)
    fprintf(stderr, "[%d]", codeend - ((code_t*)obj->codestart));
  
  close_buffer_use(codeend);
  SET_CODEMODE(obj, "normal");

#if CODE_DUMP
  obj->chained_list = psyco_codebuf_chained_list;
  psyco_codebuf_chained_list = obj;
#endif
}

/* int psyco_tie_code_buffer(PsycoObject* po) */
/* { */
/*   CodeBufferObject* b = po->respawn_proxy; */
/*   global_entries_t* ge = GET_UNUSED_SNAPSHOT(b->snapshot); */
/*   if (psyco_snapshot(b, po, ge)) */
/*     return -1; */
/*   po->respawn_cnt = 0; */
/*   return 0; */
/* } */

DEFINEFN
void psyco_emergency_enlarge_buffer(code_t** pcode, code_t** pcodelimit)
{
  code_t* code = *pcode;
  code_t* nextcode;
  if (code - *pcodelimit > GUARANTEED_MINIMUM - MAXIMUM_SIZE_OF_FAR_JUMP)
    Py_FatalError("psyco: code buffer overflowing");

  nextcode = get_next_buffer(pcodelimit);
  debug_printf(2, ("emergency enlarge buffer %p -> %p\n", code, nextcode));
  JUMP_TO(nextcode);
  close_buffer_use(code);

  *pcode = insn_code_label(nextcode);
}

#if CODE_DUMP
DEFINEFN
void psyco_dump_bigbuffers(FILE* f)
{
  codemanager_buf_t* b;
  for (b = completed_big_buffers; b; b = b->next)
    {
      char* start = ((char*) b) - BUFFER_START_OFFSET;
      size_t size = b->position-start;
      fprintf(f, "BigBuffer 0x%lx %d\n", (long) start, size);
      fwrite(start, 1, size, f);
    }
  for (b = big_buffers; b; b = b->next)
    {
      char* start = ((char*) b) - BUFFER_START_OFFSET;
      size_t size = b->position-start;
      fprintf(f, "BigBuffer 0x%lx %d\n", (long) start, size);
      fwrite(start, 1, size, f);
      if (b->inuse)
        fprintf(stderr, "warning, BigBuffer at %p still in use\n",
                b->position);
    }
}
#endif


/*****************************************************************/

static PyObject* trashed = NULL;

DEFINEFN
void psyco_trash_object(PyObject* obj)
{
  Py_XDECREF(trashed);
  trashed = obj;
}


/*****************************************************************/

static PyObject* codebuf_repr(CodeBufferObject* self)
{
  char buf[100];
  sprintf(buf, "<code buffer ptr %p at %p>",
	  self->codestart, self);
  return PyString_FromString(buf);
}

static void codebuf_dealloc(CodeBufferObject* self)
{
#if CODE_DUMP
  CodeBufferObject** ptr = &psyco_codebuf_chained_list;
/*void** chain;*/
  while (*ptr != NULL)
    {
      if (*ptr == self)
        {
          *ptr = self->chained_list;
          break;
        }
      ptr = &((*ptr)->chained_list);
    }
/*   for (chain = psyco_codebuf_spec_dict_list; chain; chain=(void**)*chain) */
/*     if (self->codestart < (code_t*)chain && (code_t*)chain <= self->codeend) */
/*       assert(!"releasing a code buffer with a spec_dict"); */
#endif
  debug_printf(3, ("releasing code buffer %p at %p\n",
                   self->codestart, self));
  fpo_release(&self->snapshot);
  
/* #if defined(ALL_CHECKS) && defined(STORE_CODE_END) */
/*   if (self->codeend != NULL) */
/*     { */
/*       * do not actully release, to detect calls to released code * */
/*       * 0xCC is the breakpoint instruction (INT 3) * */
/*       memset(self->codestart, 0xCC, self->codeend - self->codeptr); */
/*       return; */
/*     } */
/* #endif */
    
  PyObject_Del(self);
}

DEFINEVAR
PyTypeObject CodeBuffer_Type = {
	PyObject_HEAD_INIT(NULL)
	0,			/*ob_size*/
	"CodeBuffer",		/*tp_name*/
	sizeof(CodeBufferObject),	/*tp_basicsize*/
	0,			/*tp_itemsize*/
	/* methods */
	(destructor)codebuf_dealloc, /*tp_dealloc*/
	0,			/*tp_print*/
	0,			/*tp_getattr*/
	0,			/*tp_setattr*/
	0,			/*tp_compare*/
	(reprfunc)codebuf_repr,	/*tp_repr*/
	0,			/*tp_as_number*/
	0,			/*tp_as_sequence*/
	0,			/*tp_as_mapping*/
	0,			/*tp_hash*/
	0,			/*tp_call*/
};
