#include "../processor.h"
#include "iencoding.h"
#include "../dispatcher.h"
#include "../codemanager.h"
#include "../Python/frames.h"


/* define to copy static machine code in the heap before running it.
   I've seen some Linux distributions in which the static data pages
   are not executable by default. */
#define COPY_CODE_IN_HEAP


/* glue code for psyco_processor_run(). */
static code_t glue_run_code[] = {
  0x8B, 0x44, 0x24, 4,          /*   MOV EAX, [ESP+4]  (code target)   */
  0x8B, 0x4C, 0x24, 8,          /*   MOV ECX, [ESP+8]  (stack end)     */
  0x8B, 0x54, 0x24, 12,         /*   MOV EDX, [ESP+12] (initial stack) */
  PUSH_REG_INSTR(REG_386_EBP),  /*   PUSH EBP        */
  PUSH_REG_INSTR(REG_386_EBX),  /*   PUSH EBX        */
  PUSH_REG_INSTR(REG_386_ESI),  /*   PUSH ESI        */
  PUSH_REG_INSTR(REG_386_EDI),  /*   PUSH EDI        */
  0x8B, 0x5C, 0x24, 32,         /*   MOV EBX, [ESP+32] (finfo frame stack ptr) */
#ifdef __APPLE__
  /* Align stack on 16-byte boundary for MacOS X */
  0x83, 0xEC, 8,                /*   SUB ESP, 8      */
#endif
  0x6A, -1,                     /*   PUSH -1         */
  0x89, 0x23,                   /*   MOV [EBX], ESP  */
  0xEB, +5,                     /*   JMP Label2      */
                                /* Label1:           */
  0x83, 0xE9, 4,                /*   SUB ECX, 4      */
  0xFF, 0x31,                   /*   PUSH [ECX]      */
                                /* Label2:           */
  0x39, 0xCA,                   /*   CMP EDX, ECX    */
  0x75, -9,                     /*   JNE Label1      */
  0xFF, 0xD0,                   /*   CALL *EAX     (callee removes args)  */
#ifdef __APPLE__
  /* Restore stack from 16-byte alignment on MacOS X */
  0x83, 0xC4, 8,                /*   ADD ESP, 8      */
#endif
  POP_REG_INSTR(REG_386_EDI),   /*   POP EDI         */
  POP_REG_INSTR(REG_386_ESI),   /*   POP ESI         */
  POP_REG_INSTR(REG_386_EBX),   /*   POP EBX         */
  POP_REG_INSTR(REG_386_EBP),   /*   POP EBP         */
  0xC3,                         /*   RET             */
};

typedef PyObject* (*glue_run_code_fn) (code_t* code_target,
				       long* stack_end,
				       long* initial_stack,
				       struct stack_frame_info_s*** finfo);

#ifdef COPY_CODE_IN_HEAP
static glue_run_code_fn glue_run_code_1;
#else
# define glue_run_code_1 ((glue_run_code_fn) glue_run_code)
#endif

DEFINEFN
PyObject* psyco_processor_run(CodeBufferObject* codebuf,
                              long initial_stack[],
                              struct stack_frame_info_s*** finfo,
                              PyObject* tdict)
{
  int argc = RUN_ARGC(codebuf);
  return glue_run_code_1(codebuf->codestart, initial_stack + argc,
                         initial_stack, finfo);
}

/* call a C function with a variable number of arguments */
DEFINEVAR long (*psyco_call_var) (void* c_func, int argcount, long arguments[]);

static code_t glue_call_var[] = {
	0x53,			/*   PUSH EBX                      */
	0x8B, 0x5C, 0x24, 12,	/*   MOV EBX, [ESP+12]  (argcount) */
	0x8B, 0x44, 0x24, 8,	/*   MOV EAX, [ESP+8]   (c_func)   */
#ifdef __APPLE__
    /* Align stack on 16-byte boundary for MacOS X */
    0x83, 0xEC, 8,                /*   SUB ESP, 8      */
#endif
	0x09, 0xDB,		/*   OR EBX, EBX                   */
	0x74, +16,		/*   JZ Label1                     */
#ifdef __APPLE__
	/* Arguments are 8 bytes further up stack on MacOS X */
	0x8B, 0x54, 0x24, 24,	/*   MOV EDX, [ESP+24] (arguments) */
#else
	0x8B, 0x54, 0x24, 16,	/*   MOV EDX, [ESP+16] (arguments) */
#endif
	0x8D, 0x0C, 0x9A,	/*   LEA ECX, [EDX+4*EBX]          */
				/* Label2:                         */
	0x83, 0xE9, 4,		/*   SUB ECX, 4                    */
	0xFF, 0x31,		/*   PUSH [ECX]                    */
	0x39, 0xCA,		/*   CMP EDX, ECX                  */
	0x75, -9,		/*   JNE Label2                    */
				/* Label1:                         */
	0xFF, 0xD0,		/*   CALL *EAX                     */
#ifdef __APPLE__
    /* Restore stack from 16-byte alignment on MacOS X */
    0x83, 0xC4, 8,                /*   ADD ESP, 8      */
#endif
	0x8D, 0x24, 0x9C,	/*   LEA ESP, [ESP+4*EBX]          */
	0x5B,			/*   POP EBX                       */
	0xC3,			/*   RET                           */
};

/* check for signed integer multiplication overflow */
DEFINEVAR char (*psyco_int_mul_ovf) (long a, long b);

static code_t glue_int_mul[] = {
  0x8B, 0x44, 0x24, 8,          /*   MOV  EAX, [ESP+8]  (a)   */
  0x0F, 0xAF, 0x44, 0x24, 4,    /*   IMUL EAX, [ESP+4]  (b)   */
  0x0F, 0x90, 0xC0,             /*   SETO AL                  */
  0xC3,                         /*   RET                      */
};


#ifdef COPY_CODE_IN_HEAP
static code_t* internal_copy_code(void* source, int size) {
	CodeBufferObject* codebuf = psyco_new_code_buffer(NULL, NULL, NULL);
	code_t* code = codebuf->codestart;
	memcpy(code, source, size);
	SHRINK_CODE_BUFFER(codebuf, code+size, "glue");
	return code;
}
#  define COPY_CODE(target, source, type)   do {			\
	target = (type) internal_copy_code(source, sizeof(source));	\
} while (0)
#else
#  define COPY_CODE(target, source, type)   (target = (type) source)
#endif


INITIALIZATIONFN
void psyco_processor_init(void)
{
#ifdef COPY_CODE_IN_HEAP
  COPY_CODE(glue_run_code_1,    glue_run_code,     glue_run_code_fn);
#endif
  COPY_CODE(psyco_int_mul_ovf,  glue_int_mul,      char(*)(long, long));
  COPY_CODE(psyco_call_var,     glue_call_var,     long(*)(void*, int, long[]));
}


DEFINEFN struct stack_frame_info_s**
psyco_next_stack_frame(struct stack_frame_info_s** finfo)
{
	/* Hack to pick directly from the machine stack the stored
	   "stack_frame_info_t*" pointers */
	return (struct stack_frame_info_s**)
		(((char*) finfo) - finfo_last(*finfo)->link_stack_depth);
}
