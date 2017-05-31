/*
 * OS-specific utilities.
 */

/* allocate 'basicsize' bytes, or possibly a multiple of it if allocating
   large blocks of memory is better.  The allocated address is stored
   in '*result'.  The total allocated size is returned, or 0 to try some
   other allocation method. */
extern long psyco_allocate_executable_buffer(long basicsize, char **result);
