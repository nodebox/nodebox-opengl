#include "psyco.h"
#if HEAVY_MEM_CHECK

#include <Python.h>
#undef PyMem_MALLOC
#undef PyMem_REALLOC
#undef PyMem_FREE

EXTERNFN void* memchk_ef_malloc(int size);
EXTERNFN void memchk_ef_free(void* data);
EXTERNFN void* memchk_ef_realloc(void* data, int nsize);

#define PyMem_MALLOC   memchk_ef_malloc
#define PyMem_REALLOC  memchk_ef_realloc
#define PyMem_FREE     memchk_ef_free

#endif
