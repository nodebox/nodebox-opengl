 /***************************************************************/
/***         Support to manage the emitted code chunks         ***/
 /***************************************************************/

#ifndef _CODEMANAGER_H
#define _CODEMANAGER_H


#include "psyco.h"
#include "dispatcher.h"


#define WARN_TOO_MANY_BUFFERS    6    /* to detect missing buffer unlocks */


/* a CodeBufferObject is a pointer to emitted code.
   The 'state' PsycoObject records the state of the compiler at
   the start of the emission of code. Consider this field as private.
   Future versions of the code manager will probably encode the recorded
   states in a more sophisticated form than just a dump copy.
   (There are usually a lot of small CodeBufferObjects, so if each
   one has a full copy of the state big projects will explode the memory.)
*/
struct CodeBufferObject_s {
	PyObject_HEAD
	void* codestart;
	FrozenPsycoObject snapshot;

#if CODE_DUMP
	char* codemode;
	CodeBufferObject* chained_list;
#endif
};

#if CODE_DUMP
EXTERNVAR CodeBufferObject* psyco_codebuf_chained_list;
EXTERNVAR void** psyco_codebuf_spec_dict_list;
EXTERNFN void psyco_dump_bigbuffers(FILE* f);
# define SET_CODEMODE(b, mode)   ((b)->codemode = (mode))
#else
# define SET_CODEMODE(b, mode)   do { } while (0)   /* nothing */
#endif


#define CodeBuffer_Check(v)	((v)->ob_type == &CodeBuffer_Type)
EXTERNVAR PyTypeObject CodeBuffer_Type;


/* starts a new code buffer. The limit is returned in the optional last argument.
   'po' is the state of the compiler at this point, of which a
   frozen copy will be made. It can be NULL. If not, set 'ge' as in
   psyco_compile(). */
EXTERNFN
CodeBufferObject* psyco_new_code_buffer(PsycoObject* po, global_entries_t* ge, code_t** plimit);

/* creates a CodeBufferObject pointing to an already existing code target */
EXTERNFN
CodeBufferObject* psyco_proxy_code_buffer(PsycoObject* po, global_entries_t* ge);

#if 0  /* creates a minimal CodeBufferObject with only a code pointer */
EXTERNFN
CodeBufferObject* psyco_minimal_code_buffer(code_t* code);
#endif

/* shrink a buffer returned by new_code_buffer() */
EXTERNFN
void psyco_shrink_code_buffer(CodeBufferObject* obj, code_t* codeend);

/* emergency enlarge a buffer (by coding a jump to a new buffer) */
EXTERNFN
void psyco_emergency_enlarge_buffer(code_t** pcode, code_t** pcodelimit);

EXTERNFN
int psyco_locked_buffers(void);

#define SHRINK_CODE_BUFFER(obj, nend, mode)    do {    \
      psyco_shrink_code_buffer(obj, nend);             \
      SET_CODEMODE(obj, mode);                         \
} while (0)


/* a replacement for Py_XDECREF(obj) which does not release the object
   immediately, but only at the next call to psyco_trash_object() */
EXTERNFN
void psyco_trash_object(PyObject* obj);


#endif /* _CODEMANAGER_H */
