#include "frames.h"
#include "pyver.h"
#include "../codemanager.h"
#include "../stats.h"
#include "../vcompiler.h"
#include "../Objects/pobject.h"

#include <opcode.h>


 /***************************************************************/

/* turn a running frame into its Psyco equivalent, a PsycoObject.
   Return Py_None if the frame cannot be turned into a PsycoObject.
   Never sets an exception. */
PSY_INLINE PyObject* PsycoObject_FromFrame(PyFrameObject* f, int recursion)
{
	int i, extras, module;
	vinfo_t* v;
	PsycoObject* po;
	RunTimeSource rsrc;
	source_known_t* sk;
	PyCodeObject* co = f->f_code;
	PyObject* merge_points;

	if (f->f_stacktop == NULL) {
		/* cannot patch a frame other than the top (running) one */
		goto fail;
	}
        module = f->f_globals == f->f_locals;
	merge_points = PyCodeStats_MergePoints(PyCodeStats_Get(co), module);
	if (merge_points == Py_None) {
		/* unsupported bytecode instructions */
		goto fail;
	}
	if (psyco_mp_flags(merge_points) & MP_FLAGS_HAS_FINALLY) {
		/* incompatible handling of 'finally' blocks */
		goto fail;
	}

	/* the local variables are assumed to be stored as 'fast' variables,
	   not in the f_locals dictionary.  This is currently asserted by
	   the fact that LOAD_NAME and STORE_NAME opcodes are not supported
	   at all.  XXX support LOAD_NAME / STORE_NAME / DELETE_NAME */
	extras = (f->f_valuestack - f->f_localsplus) + co->co_stacksize;

	po = PsycoObject_New(INDEX_LOC_LOCALS_PLUS + extras);
	po->stack_depth = INITIAL_STACK_DEPTH;
	po->vlocals.count = INDEX_LOC_LOCALS_PLUS + extras;
	INIT_PROCESSOR_PSYCOOBJECT(po);
	po->pr.auto_recursion = AUTO_RECURSION(recursion);

	/* initialize po->vlocals */
	Py_INCREF(f->f_globals);
	sk = sk_new((long) f->f_globals, SkFlagPyObj);
	LOC_GLOBALS = vinfo_new(CompileTime_NewSk(sk));
	
	/* move the current arguments, locals, and object stack into
	   their target place */
	for (i = f->f_stacktop - f->f_localsplus; i--; ) {
		PyObject* o = f->f_localsplus[i];
		po->stack_depth += sizeof(long);
		if (o == NULL) {
			/* uninitialized local variable,
			   the corresponding stack position is not used */
			v = psyco_vi_Zero();
		}
		else {
			/* XXX do something more intelligent for cell and
			       free vars */
			/* arguments get borrowed references */
			rsrc = RunTime_NewStack(po->stack_depth, false, false);
			v = vinfo_new(rsrc);
		}
		LOC_LOCALS_PLUS[i] = v;
	}
	/* the rest of the stack in LOC_LOCALS_PLUS is
	   initialized to NULL by PsycoObject_New() */

	/* store the code object */
	po->pr.co = co;
	Py_INCREF(co);  /* XXX never freed */
	po->pr.next_instr = f->f_lasti;
	pyc_data_build(po, merge_points);
	if (f->f_iblock) {
		po->pr.iblock = f->f_iblock;
		memcpy(po->pr.blockstack, f->f_blockstack,
		       sizeof(PyTryBlock)*po->pr.iblock);
	}

	/* set up the CALL return address */
	po->stack_depth += sizeof(long);
	rsrc = RunTime_NewStack(po->stack_depth, false, false);
	LOC_CONTINUATION = vinfo_new(rsrc);
	psyco_assert_coherent(po);
	return (PyObject*) po;

 fail:
	Py_INCREF(Py_None);
	return Py_None;
}

/* same as PsycoObject_FromFrame() on any not-yet-started frame with the
   given code object */
PSY_INLINE PyObject* PsycoObject_FromCode(PyCodeObject* co,
                                      PyObject* globals,
                                      int recursion,
                                      int module)
{
	int i, argc, ncells, nfrees, extras;
	PyObject* merge_points;
	PsycoObject* po;
	Source rsrc;
	source_known_t* sk;
	vinfo_t* v;
	
	merge_points = PyCodeStats_MergePoints(PyCodeStats_Get(co), module);
	if (merge_points == Py_None) {
		/* unsupported bytecode instructions */
		goto fail;
	}

	ncells = PyTuple_GET_SIZE(co->co_cellvars);
	nfrees = PyTuple_GET_SIZE(co->co_freevars);
	extras = co->co_stacksize + co->co_nlocals + ncells + nfrees;

	po = PsycoObject_New(INDEX_LOC_LOCALS_PLUS + extras);
	po->stack_depth = INITIAL_STACK_DEPTH;
	po->vlocals.count = INDEX_LOC_LOCALS_PLUS + extras;
	INIT_PROCESSOR_PSYCOOBJECT(po);
	po->pr.auto_recursion = AUTO_RECURSION(recursion);

	/* initialize po->vlocals */
	Py_INCREF(globals);
	sk = sk_new((long) globals, SkFlagPyObj);
	LOC_GLOBALS = vinfo_new(CompileTime_NewSk(sk));

	argc = co->co_argcount;
	if (co->co_flags & CO_VARARGS)
		argc++;
	if (co->co_flags & CO_VARKEYWORDS)
		argc++;

	/* initialize the free and cell vars */
	i = co->co_nlocals + ncells + nfrees;
	if (ncells || nfrees) {
		while (i > co->co_nlocals) {
			po->stack_depth += sizeof(long);
			/* borrowed references from the frame object */
			rsrc = RunTime_NewStack(po->stack_depth, false, false);
			v = vinfo_new(rsrc);
			LOC_LOCALS_PLUS[--i] = v;
		}
		/* skip the unbound local variables */
		po->stack_depth += sizeof(long) * (i-argc);
	}
	/* initialize the local variables to zero (unbound) */
	while (i > argc) {
		v = psyco_vi_Zero();
		LOC_LOCALS_PLUS[--i] = v;
	}
	/* initialize the keyword arguments dict */
	if (co->co_flags & CO_VARKEYWORDS) {
		po->stack_depth += sizeof(long);
		rsrc = RunTime_NewStack(po->stack_depth, false, false);
		v = vinfo_new(rsrc);
		/* known to be a dict */
                /*Psyco_AssertType(NULL, v, &PyDict_Type);*/
		rsrc = CompileTime_New((long) &PyDict_Type);
                v->array = array_new(FIELDS_TOTAL(OB_type));
                v->array->items[iOB_TYPE] = vinfo_new(rsrc);
		LOC_LOCALS_PLUS[--i] = v;
	}
	/* initialize the extra arguments tuple */
	if (co->co_flags & CO_VARARGS) {
		po->stack_depth += sizeof(long);
		rsrc = RunTime_NewStack(po->stack_depth, false, false);
		v = vinfo_new(rsrc);
		/* known to be a tuple */
		rsrc = CompileTime_New((long) &PyTuple_Type);
		v->array = array_new(iOB_TYPE+1);
		v->array->items[iOB_TYPE] = vinfo_new(rsrc);
		LOC_LOCALS_PLUS[--i] = v;
	}
	/* initialize the regular arguments */
	while (i > 0) {
		/* XXX do something more intelligent for cell and
		       free vars */
		po->stack_depth += sizeof(long);
		/* arguments get borrowed references */
		rsrc = RunTime_NewStack(po->stack_depth, false, false);
		v = vinfo_new(rsrc);
		LOC_LOCALS_PLUS[--i] = v;
	}
	/* the rest of the stack in LOC_LOCALS_PLUS is
	   initialized to NULL by PsycoObject_New() */

	/* store the code object */
	po->pr.co = co;
	Py_INCREF(co);  /* XXX never freed */
	pyc_data_build(po, merge_points);

	/* set up the CALL return address */
	po->stack_depth += sizeof(long);
	rsrc = RunTime_NewStack(po->stack_depth, false, false);
	LOC_CONTINUATION = vinfo_new(rsrc);
	return (PyObject*) po;

 fail:
	Py_INCREF(Py_None);
	return Py_None;
}

DEFINEFN
PyObject* PsycoCode_CompileCode(PyCodeObject* co,
                                PyObject* globals,
                                int recursion,
                                int module)
{
	mergepoint_t* mp;
	PsycoObject* po;
	PyObject* o = PsycoObject_FromCode(co, globals, recursion, module);
	if (o == Py_None)
		return o;

	/* compile the function */
	po = (PsycoObject*) o;
	mp = PsycoObject_Ready(po);
	return (PyObject*) psyco_compile_code(po, mp);
}

DEFINEFN
PyObject* PsycoCode_CompileFrame(PyFrameObject* f, int recursion)
{
	mergepoint_t* mp;
	PsycoObject* po;
	PyObject* o = PsycoObject_FromFrame(f, recursion);
	if (o == Py_None)
		return o;

	/* compile the function */
	po = (PsycoObject*) o;
	mp = psyco_exact_merge_point(po->pr.merge_points, po->pr.next_instr);
	if (mp != NULL)
		psyco_delete_unused_vars(po, &mp->entries);
	return (PyObject*) psyco_compile_code(po, mp);
}

DEFINEFN
bool PsycoCode_Run(PyObject* codebuf, PyFrameObject* f, bool entering)
{
	PyObject* tdict;
	PyFrameRuntime* fruntime;
	stack_frame_info_t** finfo;
	int err;
	long* initial_stack;
	PyObject* result;
        PyCodeObject* co = f->f_code;

	extra_assert(codebuf != NULL);
	extra_assert(CodeBuffer_Check(codebuf));
	
	/* over the current Python frame, a lightweight chained list of
	   Psyco frames will be built. Mark the current Python frame as
	   the starting point of this chained list. */
	tdict = psyco_thread_dict();
	if (tdict==NULL) return false;
	fruntime = PyCStruct_NEW(PyFrameRuntime, PyFrameRuntime_dealloc);
        Py_INCREF(f);
        fruntime->cs_key = (PyObject*) f;
        fruntime->psy_frames_start = &finfo;
        fruntime->psy_code = co;
        fruntime->psy_globals = f->f_globals;
	extra_assert(PyDict_GetItem(tdict, (PyObject*) f) == NULL);
	err = PyDict_SetItem(tdict, (PyObject*) f, (PyObject*) fruntime);
	Py_DECREF(fruntime);
	if (err) return false;
	/* Warning, no 'return' between this point and the PyDict_DelItem()
	   below */
        
	/* get the actual arguments */
	initial_stack = (long*) f->f_localsplus;

	/* run! */
        Py_INCREF(codebuf);
	result = psyco_processor_run((CodeBufferObject*) codebuf,
				     initial_stack, &finfo, tdict);
	Py_DECREF(codebuf);
	psyco_trash_object(NULL);  /* free any trashed object now */

#if CODE_DUMP >= 2
        psyco_dump_code_buffers();
#endif
	if (PyDict_DelItem(tdict, (PyObject*) f)) {
		Py_XDECREF(result);
		result = NULL;
	}
	if (result == NULL) {
		PyObject *exc, *value, *tb;
		if (entering) {
			/* Nothing special to worry in this case,
			   eval_frame() will return right away */
			extra_assert(PyErr_Occurred());  /* exception */
			return false;
		}
		
		/* Attention: the maybe_call_line_trace() call of ceval.c:822
		   (Python 2.3b1) will *not* reload f->f_lasti and
		   f->f_stacktop if these get modified in case of exception!
		   We definitely cannot modify the stack top. We *must*
		   however empty the block stack to prevent exception
		   handlers to be entered --- they have already been run by
		   Psyco! */
		PyErr_Fetch(&exc, &value, &tb);
		extra_assert(exc != NULL);      /* exception */
                f->f_iblock = 0;
		
		/* We cannot prevent Python from calling PyTraceBack_Here()
		   when this function returns, althought Psyco has already
		   recorded a traceback. We remove Psyco's traceback and
		   make sure Python will re-insert an equivalent one. */
		if (tb != NULL) {  /* should normally never be NULL */
			/* no C interface to tb_lasti; call it via Python */
			PyObject *tb_next, *tb_lasti;
			tb_lasti = PyObject_GetAttrString(tb, "tb_lasti");
			extra_assert(tb_lasti != NULL);
			extra_assert(PyInt_Check(tb_lasti));
			f->f_lasti = PyInt_AS_LONG(tb_lasti);
			Py_DECREF(tb_lasti);

			tb_next = PyObject_GetAttrString(tb, "tb_next");
			extra_assert(tb_next != NULL);
			Py_DECREF(tb);
			tb = tb_next;
		}
		PyErr_Restore(exc, value, tb);
		return false;
	}
	else {
		/* to emulate the return, move the current position to
		   the end of the function code.  We assume that the
		   last instruction of any code object is a RETURN_VALUE. */
		PyObject** p;
		int new_i = PyString_GET_SIZE(co->co_code) - 1;
		/* Python 2.5: the bytecode doesn't always end with a
		   RETURN_VALUE, but surely there must be one *somewhere* */
		while (PyString_AS_STRING(co->co_code)[new_i] != RETURN_VALUE){
			--new_i;
			psyco_assert(new_i >= 0);
		}
#if PY_VERSION_HEX >= 0x02030000   /* 2.3 */
		/* dubious compatibility hack for Python 2.3, in which f_lasti
		   no longer always refer to the instruction that will be
		   executed just after the current trace hook returns */
	        new_i -= entering;
#endif
		f->f_lasti = new_i;
		f->f_iblock = 0;

		/* free the stack */
		for (p=f->f_stacktop; --p >= f->f_valuestack; ) {
			Py_XDECREF(*p);
			*p = NULL;
		}
		/* push the result alone on the stack */
		p = f->f_valuestack;
		*p++ = result;  /* consume a ref */
		f->f_stacktop = p;

		extra_assert(!PyErr_Occurred());
		return true;
	}
}


 /***************************************************************/

#define FRAME_STACK_ALLOC_BY	83   /* about 1KB */

DEFINEFN
stack_frame_info_t* psyco_finfo(PsycoObject* caller, PsycoObject* callee)
{
	static stack_frame_info_t* current = NULL;
	static stack_frame_info_t* end = NULL;
	
	Source sglobals;
	stack_frame_info_t* p;
	int inlining = caller != NULL && caller->pr.is_inlining;
	
	if (end - current <= inlining) {
		psyco_memory_usage += sizeof(stack_frame_info_t) *
			FRAME_STACK_ALLOC_BY;
		current = PyMem_NEW(stack_frame_info_t, FRAME_STACK_ALLOC_BY);
		if (current == NULL)
			OUT_OF_MEMORY();
		end = current + FRAME_STACK_ALLOC_BY;
	}
	p = current;
	current += inlining + 1;
#if NEED_STACK_FRAME_HACK
	p->link_stack_depth = -inlining;
#endif
	p->co = callee->pr.co;
	sglobals = callee->vlocals.items[INDEX_LOC_GLOBALS]->source;
	if (is_compiletime(sglobals))
		p->globals = (PyObject*) CompileTime_Get(sglobals)->value;
	else
		p->globals = NULL;  /* uncommon */
	if (inlining) {
		(p+1)->co = caller->pr.co;
		sglobals = caller->vlocals.items[INDEX_LOC_GLOBALS]->source;
		if (is_compiletime(sglobals))
			(p+1)->globals = (PyObject*)
				CompileTime_Get(sglobals)->value;
		else
			(p+1)->globals = NULL;  /* uncommon */
	}
	return p;
}

DEFINEFN
void PyFrameRuntime_dealloc(PyFrameRuntime* self)
{
	/* nothing */
}

PSY_INLINE PyFrameObject* psyco_build_pyframe(PyObject* co, PyObject* globals,
					      PyThreadState* tstate)
{
	PyFrameObject* back;
	PyFrameObject* result;
	
	/* frame objects are not created in stack order
	   with Psyco, so it's probably better not to
	   create plain wrong chained lists */
	back = tstate->frame;
	tstate->frame = NULL;
	result = PyFrame_New(tstate, (PyCodeObject*) co, globals, NULL);
	if (result == NULL)
		OUT_OF_MEMORY();
        result->f_lasti = -1;  /* can be used to identify emulated frames */
	tstate->frame = back;
	return result;
}

DEFINEFN
PyFrameObject* psyco_emulate_frame(PyObject* o)
{
	if (PyFrame_Check(o)) {
		/* a real Python frame */
		Py_INCREF(o);
		return (PyFrameObject*) o;
	}
	else {
		/* a Psyco frame: emulate it */
		PyObject* co = PyTuple_GetItem(o, 0);
		PyObject* globals = PyTuple_GetItem(o, 1);
		extra_assert(co != NULL);
		extra_assert(globals != NULL);
		return psyco_build_pyframe(co, globals, PyThreadState_GET());
	}
}

struct sfitmp_s {
	stack_frame_info_t** fi;
	struct sfitmp_s* next;
};

static PyObject* pvisitframes(PyObject*(*callback)(PyObject*,void*),
			      void* data)
{
        /* Whenever we run Psyco-produced machine code, we mark the current
           Python frame as the starting point of a chained list of Psyco
           frames. The machine code will update this chained list so that
           psyco_next_stack_frame() can be used to visit the list from
           the outermost to the innermost frames. Note that the list does
           not contain the first Psyco frame, the one directly run by a
           call to psyco_processor_run(). This still gives the expected
           result, because PsycoFunctionObjects are only supposed to be
           called by proxy codes (see psyco_proxycode()). This proxy
           code itself has a frame. It replaces the missing Psyco frame.
           XXX this would no longer work if we filled the emulated frames
               with more information, like local variables */

	PyObject* result = NULL;
	PyFrameRuntime* fstart;
	PyObject* tdict = psyco_thread_dict();
	PyFrameObject* f = PyThreadState_Get()->frame;

	RECLIMIT_SAFE_ENTER();
	while (f != NULL) {
		/* is this Python frame the starting point of a chained
		   list of Psyco frames ? */
		fstart = (PyFrameRuntime*) PyDict_GetItem(tdict, (PyObject*) f);
		if (fstart != NULL) {
			/* Yes. Get the list start. */
			struct sfitmp_s* revlist;
			struct sfitmp_s* p;
			PyObject* o;
			PyObject* g;
			long tag;
			stack_frame_info_t** f1;
			stack_frame_info_t** finfo;
			stack_frame_info_t* fdata;
			stack_frame_info_t* flimit;
			finfo = *(fstart->psy_frames_start);

			/* Enumerate the frames and store them in a
			   last-in first-out linked list. The end is marked by
			   a pointer with an odd integer value (actually with
                           i386 the least significant byte of the integer value
                           is -1, and with ivm the end pointer's value is
                           exactly 1; but real pointers cannot be odd at all
                           because they are aligned anyway). */
			revlist = NULL;
			for (f1 = finfo; (((long)(*f1)) & 1) == 0;
			     f1 = psyco_next_stack_frame(f1)) {
				p = (struct sfitmp_s*)
					PyMem_MALLOC(sizeof(struct sfitmp_s));
				if (p == NULL)
					OUT_OF_MEMORY();
				p->fi = f1;
				p->next = revlist;
				revlist = p;
#if NEED_STACK_FRAME_HACK
				if ((*f1)->link_stack_depth == 0)
					break; /* stack top is an inline frame */
#endif
			}

			/* now actually visit them in the correct order */
			while (revlist) {
				p = revlist;
				/* a Psyco frame is represented as
				   (co, globals, address_of(*fi)) */
				if (result == NULL) {
					tag = (long)(p->fi);
					fdata = *p->fi;
					flimit = finfo_last(fdata);
					while (1) {
						g = fdata->globals;
						if (g == NULL)
							g = f->f_globals;
						o = Py_BuildValue("OOl",
								  fdata->co, g,
								  tag);
						if (o == NULL)
							OUT_OF_MEMORY();
						result = callback(o, data);
						Py_DECREF(o);
						if (result != NULL)
							break;
						if (fdata == flimit)
							break;
						fdata++, tag--;
					}
				}
				revlist = p->next;
				PyMem_FREE(p);
			}
			if (result != NULL)
				break;

			/* there is still the real Python frame
			   which is shadowed by a Psyco frame, i.e. a
			   proxy function. Represented as
			   (co, globals, f) */
			o = Py_BuildValue("OOO",
					  fstart->psy_code,
					  fstart->psy_globals,
					  f);
			if (o == NULL)
				OUT_OF_MEMORY();
			result = callback(o, data);
			Py_DECREF(o);
		}
		else {
			/* a real unshadowed Python frame */
			result = callback((PyObject*) f, data);
		}
		if (result != NULL)
			break;
		f = f->f_back;
	}
        RECLIMIT_SAFE_LEAVE();
	return result;
}



static PyObject* visit_nth_frame(PyObject* o, void* n)
{
	/* count the calls to the function and return 'o' when
	   the counter reaches zero */
	if (!--*(int*)n) {
		Py_INCREF(o);
		return o;
	}
	return NULL;
}

static PyObject* visit_prev_frame(PyObject* o, void* data)
{
	PyObject* cmp = *(PyObject**) data;

	if (cmp != NULL) {
		/* still searching */
		if (PyFrame_Check(o) || PyFrame_Check(cmp)) {
			if (o != cmp) return NULL;
		}
		else {
			PyObject* p1;
			PyObject* p2;

			p1 = PyTuple_GetItem(o,   2);  /* tag */
			p2 = PyTuple_GetItem(cmp, 2);
			if (PyObject_Compare(p1, p2) != 0) return NULL;

			p1 = PyTuple_GetItem(o,   0);  /* code */
			p2 = PyTuple_GetItem(cmp, 0);
			if (p1 != p2) return NULL;

			p1 = PyTuple_GetItem(o,   1);  /* globals */
			p2 = PyTuple_GetItem(cmp, 1);
			if (p1 != p2) return NULL;
		}
		/* found it ! We will succeed the next time
		   visit_find_frame() is called. */
		*(PyObject**) data = NULL;
		return NULL;
	}
	else {
		/* found it the previous time, now return this next 'o' */
		Py_INCREF(o);
		return o;
	}
}

DEFINEFN
PyObject* psyco_find_frame(PyObject* o)
{
	void* result;
	if (PyInt_Check(o)) {
		int depth = PyInt_AsLong(o) + 1;
		if (depth <= 0)
			depth = 1;
		result = pvisitframes(visit_nth_frame, &depth);
	}
	else {
		result = pvisitframes(visit_prev_frame, (void*) &o);
		if (result == NULL && !PyErr_Occurred() && o != NULL)
			PyErr_SetString(PyExc_PsycoError,
					"f_back is invalid when frames are no longer active");
	}
	if (result == NULL && !PyErr_Occurred())
		PyErr_SetString(PyExc_ValueError,
				"call stack is not deep enough");
	return (PyObject*) result;
}

static PyObject* visit_get_globals(PyObject* o, void* ignored)
{
	if (PyFrame_Check(o))
		return ((PyFrameObject*) o)->f_globals;
	else
		return PyTuple_GetItem(o, 1);
}
DEFINEFN
PyObject* psyco_get_globals(void)
{
	PyObject* result = pvisitframes(visit_get_globals, NULL);
	if (result == NULL)
		psyco_fatal_msg("sorry, don't know what to do with no globals");
	return result;
}

static PyFrameObject* cached_frame = NULL;
static PyObject* visit_first_frame(PyObject* o, void* ts)
{
	if (PyFrame_Check(o)) {
		/* a real Python frame: don't return a new reference */
		return (PyObject*) o;
	}
	else {
		/* a Psyco frame: emulate it */
		/* we can't return a new reference, so we have to remember
		   the last frame we emulated and free it now.  This is
		   not too bad since we can use this as a cache and avoid
		   rebuilding the new emulated frame all the time. */
		PyFrameObject* f;
		PyFrameObject* newf;
		PyObject* co = PyTuple_GetItem(o, 0);
		PyObject* globals = PyTuple_GetItem(o, 1);
		PyThreadState* tstate = (PyThreadState*) ts;
		extra_assert(co != NULL);
		extra_assert(globals != NULL);
		while (cached_frame != NULL) {
			f = cached_frame;
			if ((PyObject*) f->f_code == co
			    && f->f_globals == globals) {
				/* reuse the cached frame */
				f->f_tstate = tstate;
				return (PyObject*) f;
			}
			cached_frame = NULL;
			Py_DECREF(f);  /* might set cached_frame again
					  XXX could this loop never end? */
		}
		newf = psyco_build_pyframe(co, globals, tstate);
		while (cached_frame != NULL) {
			/* worst-case safe...  this is unlikely */
			f = cached_frame;
			cached_frame = NULL;
			Py_DECREF(f);
		}
		cached_frame = newf;   /* transfer ownership */
		return (PyObject*) newf;
	}
}
static PyFrameObject* psyco_threadstate_getframe(PyThreadState* self)
{
	return (PyFrameObject*) pvisitframes(visit_first_frame, (void*)self);
}


 /***************************************************************/

INITIALIZATIONFN
void psyco_frames_init(void)
{
	_PyThreadState_GetFrame =
#  if PYTHON_API_VERSION < 1012
		(unaryfunc)
#  endif
		psyco_threadstate_getframe;
}
