 /***************************************************************/
/***             Processor-specific execution                  ***/
 /***************************************************************/

#ifndef _PROCESSOR_H
#define _PROCESSOR_H

#include "psyco.h"


/***************************************************************/
 /*** Execution                                               ***/

/* executes a block of code. A new stack frame is created and
   the 'initial_stack' values are PUSHed into it. The number
   of values pushed are determined by the saved arguments_count of
   the 'codebuf'.
*/
struct stack_frame_info_s;
EXTERNFN PyObject* psyco_processor_run(CodeBufferObject* codebuf,
                                       long initial_stack[],
                                       struct stack_frame_info_s*** finfo,
                                       PyObject* tdict);

#define RUN_ARGC(codebuf)                                             \
   (extra_assert(CodeBuffer_Check((codebuf))),                        \
    (int)((get_stack_depth(&((CodeBufferObject*)(codebuf))->snapshot) \
     - INITIAL_STACK_DEPTH - sizeof(long)) / sizeof(long)))

/* call a C function with a variable number of arguments
   (implemented as a pointer to assembler code) */
EXTERNVAR long (*psyco_call_var) (void* c_func, int argcount, long arguments[]);

/* check for signed integer multiplication overflow */
EXTERNVAR char (*psyco_int_mul_ovf) (long a, long b);

/* find the next stack frame
   ("next" = more recent in time = towards innermost frames) */
EXTERNFN struct stack_frame_info_s**
psyco_next_stack_frame(struct stack_frame_info_s** finfo);


#endif /* _PROCESSOR_H */
