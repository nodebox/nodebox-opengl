/* custom checking allocators a la Electric Fence */
#include "linuxmemchk.h"
#if HEAVY_MEM_CHECK
#undef NDEBUG
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#define PAGESIZE 4096
#ifndef MALLOC_BIGBUFFER
# define MALLOC_BIGBUFFER   PAGESIZE*16384
#endif


struct _alloc_s {
  void* ptr;
  int npages;
};
static void* _na_start = NULL;
static char* _na_cur;

static struct _alloc_s* _na_find(void* data)
{
  int err;
  long data1;
  struct _alloc_s* s;
  assert(_na_start+PAGESIZE <= data &&
         data < _na_start+MALLOC_BIGBUFFER-PAGESIZE);
  data1 = (long) data;
  data1 &= ~(PAGESIZE-1);
  data1 -= PAGESIZE;
  err = mprotect((void*) data1, PAGESIZE, PROT_READ|PROT_WRITE);
  assert(!err);
  s = (struct _alloc_s*) data1;
  assert(s->npages > 0);
  return s;
}

DEFINEFN
void* memchk_ef_malloc(int size)
{
  int err, npages = (size + PAGESIZE-1) / PAGESIZE + 1;
  struct _alloc_s* s;
  char* data;
  if (_na_start == NULL)
    {
      _na_start = mmap(NULL, MALLOC_BIGBUFFER, PROT_NONE,
                       MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
      assert(_na_start != MAP_FAILED);
      _na_cur = (char*) _na_start;
    }
  s = (struct _alloc_s*) _na_cur;
  _na_cur += npages * PAGESIZE;
  if (_na_cur >= ((char*) _na_start) + MALLOC_BIGBUFFER)
    {
      fprintf(stderr, "Nothing wrong so far, but MALLOC_CHECK is running out\n of mmap'ed memory.  Increase MALLOC_BIGBUFFER.\n");
      assert(0);
    }
  err = mprotect(s, npages * PAGESIZE, PROT_READ|PROT_WRITE|PROT_EXEC);
  assert(!err);
  s->ptr = data = _na_cur - /*((size+3)&~3)*/ size;
  s->npages = npages;
  err = mprotect(s, PAGESIZE, PROT_NONE);
  assert(!err);
  return data;
}

DEFINEFN
void memchk_ef_free(void* data)
{
  int err, npages;
  struct _alloc_s* s;
  if (data == NULL)
    return;
  s = _na_find(data);
  assert(s->ptr == data);
  npages = s->npages;
  s->npages = 0;
  err = mprotect(s, npages * PAGESIZE, PROT_NONE);
  assert(!err);
  //fprintf(stderr, "PyMem_FREE(%p): mprotect %p %x\n", data, s, npages*PAGESIZE);
}

DEFINEFN
void* memchk_ef_realloc(void* data, int nsize)
{
  int size;
  struct _alloc_s* s = _na_find(data);
  void* ndata = PyMem_MALLOC(nsize);

  assert(s->ptr == data);
  size = ((char*)s) + s->npages * PAGESIZE - (char*)data;
  memcpy(ndata, data, size<nsize ? size : nsize);
  PyMem_FREE(data);
  return ndata;
}


#endif  /* LINUXMEMCHK */
