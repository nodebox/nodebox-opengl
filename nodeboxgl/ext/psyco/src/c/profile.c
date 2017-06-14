#include "profile.h"
#include "stats.h"
#include "cstruct.h"
#include "Python/pyver.h"
#include "Python/frames.h"
#include "codemanager.h"


/* There are three profilers you can choose from:

   1) Profiling via Python's profiler hooks
        (active profiling)
   2) Have a parallel thread that peeks for info
        (passive profiling, rough precision, requires threads)
   3) Both
        (XXX test and compare all three choices)

   We use the tick_counter field of the PyThreadState to
   measure "execution time", on the basis that Psyco is
   good at removing opcode dispatching and the inter-opcode
   allocations, so the theory is that the more opcodes are
   executed, the better Psyco will perform on that code.
*/

/* Internal invariants in PyCodeStats:
   
	st_codebuf is NULL if not compiled yet,
		      None if the compilation failed,
		      or a real code buffer object.

	st_globals is NULL if the code should be normally executed,
		      an int if we want to accelerate that code object,
		      or the globals dictionary that st_codebuf we compiled with.

   Valid states are: (st_codebuf, st_globals)

        (NULL, NULL)         normal execution
	(NULL, rec-level)    compile at the next occasion
	(None, NULL)         compilation failed
	(codebuf, globals)   compilation succeeded
*/


/***************************************************************/
 /***   Flexibly hooking routines into Python's profiler and  ***/
  /***   tracing hooks                                         ***/

#define PyTrace_TOTAL 4


/* a hook routine returns NULL or the code buffer object containing
   the compiled code to run now. */
typedef PyObject* (*ceval_event_fn) (PyFrameObject* frame, PyObject* arg);

struct cevent_s {
	ceval_event_fn fn;
	PyObject* arg;
};
struct cevents_s {
	int count;
	struct cevent_s* items;
};
typedef struct {
	PyCStruct_HEAD
	/*PyThread_type_lock lock; not needed, changes protected by the GIL */
	struct cevents_s events[PyTrace_TOTAL];
	PyThreadState* tstate;
	int events_total;
	char current_hook;   /* 'P'rofile, 'T'race */
} ceval_events_t;

static PyObject* ceval_events_key;   /* interned string */

static void ceval_events_dealloc(ceval_events_t* cev)
{
	int i;
	/*extra_assert(PyThread_acquire_lock(cev->lock, NOWAIT_LOCK));*/
	for (i=0; i<PyTrace_TOTAL; i++) {
		PyMem_FREE(cev->events[i].items);
	}
	/*PyThread_free_lock(cev->lock);*/
}

static ceval_events_t* new_cevents(PyThreadState* tstate)
{
	ceval_events_t* cev;
	PyObject* dict = tstate->dict;

        RECLIMIT_SAFE_ENTER();
	if (dict == NULL) {
		dict = tstate->dict = PyDict_New();
		if (dict == NULL)
			OUT_OF_MEMORY();
	}
	cev = PyCStruct_NEW(ceval_events_t, ceval_events_dealloc);
	/*cev->lock = PyThread_allocate_lock();*/
	memset(cev->events, 0, sizeof(cev->events));
	cev->tstate = tstate;
	cev->events_total = 0;
	cev->current_hook = 0;
	if (PyDict_SetItem(dict, ceval_events_key, (PyObject*) cev))
		OUT_OF_MEMORY();
        RECLIMIT_SAFE_LEAVE();
	Py_DECREF(cev);  /* one ref left in dict */
	return cev;
}

PSY_INLINE ceval_events_t* get_cevents(PyThreadState* tstate)
{
	PyObject* dict = tstate->dict;
	if (dict != NULL) {
		PyObject* o = PyDict_GetItem(dict, ceval_events_key);
		if (o != NULL) {
			extra_assert(PyCStruct_Check(o));
			return (ceval_events_t*) o;
		}
	}
	return new_cevents(tstate);
}


static PyObject* deleted_ceval_hook(PyFrameObject* frame, PyObject* arg)
{
	return NULL;
}

static void set_ceval_hook(ceval_events_t* cev, int when,
			   ceval_event_fn fn, PyObject* arg)
{
	int n, i, allow;
	struct cevents_s* events;
	extra_assert(0 <= when && when < PyTrace_TOTAL);
	events = cev->events + when;
	n = events->count++;
	PyMem_RESIZE(events->items, struct cevent_s, events->count);
	if (events->items == NULL)
		OUT_OF_MEMORY();
	events->items[n].fn = fn;
	events->items[n].arg = arg;
	cev->events_total++;
	if (arg != NULL) {
		/* bound the total number of hooks by checking if there are
		   too many other hooks with the same 'fn' */
		allow = 8;
		for (i=n; --i >= 0; ) {
			if (events->items[i].fn == fn && !--allow) {
				/* too many! remove an arbitrary one */
				events->items[i].fn = &deleted_ceval_hook;
				cev->events_total--;
				break;
			}
		}
	}
}

static void unset_ceval_hook(ceval_events_t* cev, int when,
			     ceval_event_fn fn, PyObject* arg)
{
	/* warning: do not shuffle values in the events->items array to
	   compact it, because this might be called while the array is 
	   being enumerated by call_ceval_hooks() */
	int n;
	struct cevents_s* events;
	extra_assert(0 <= when && when < PyTrace_TOTAL);
	events = cev->events + when;
	n = events->count;
	while (n--) {
		if (events->items[n].fn == fn && events->items[n].arg == arg) {
			events->items[n].fn = &deleted_ceval_hook;
			cev->events_total--;
		}
	}
}

#if VERBOSE_STATS
# define set_ceval_hook(cev, when, fn, arg)   do {                             \
    stats_printf(("set_ceval_hook:   " #when ", " #fn ", " #arg " = 0x%x\n", (int)arg));  \
    set_ceval_hook(cev, when, fn, arg);                                        \
  } while (0)
# define unset_ceval_hook(cev, when, fn, arg)   do {                           \
    stats_printf(("unset_ceval_hook: " #when ", " #fn ", " #arg " = 0x%x\n", (int)arg));  \
    unset_ceval_hook(cev, when, fn, arg);                                      \
  } while (0)
#endif

PSY_INLINE bool call_ceval_hooks(ceval_events_t* cev, int what, PyFrameObject* f)
{
	bool r = true;
	int n;
	struct cevents_s* events;
	PyObject* codebuf;
	PyObject* obj;
	extra_assert(what >= 0);
	if (what >= PyTrace_TOTAL)
		return true;   /* Python >= 2.4 defines PyTrace_C_xxx */
#if VERBOSE_LEVEL >= 3
        stats_printf(("hook: %d %s\n", what, PyCodeObject_NAME(f->f_code)));
#endif
	events = cev->events + what;
	n = events->count;
	do {
		if (n == 0)
			return true;  /* done */
		n--;
		extra_assert(n < events->count);
		codebuf = events->items[n].fn(f, events->items[n].arg);
		if (events->items[n].fn == &deleted_ceval_hook) {
			events->items[n] = events->items[--events->count];
		}
	} while (codebuf == NULL);

	/* call the other hooks, if any */
	while (n != 0) {
		n--;
		extra_assert(n < events->count);
		obj = events->items[n].fn(f, events->items[n].arg);
		Py_XDECREF(obj);
		if (events->items[n].fn == &deleted_ceval_hook) {
			events->items[n] = events->items[--events->count];
		}
	}
	/* enable recursive calls to call_ceval_hooks() */
	f->f_tstate->use_tracing = 1;
	f->f_tstate->tracing--;
	/* run the compiled code */
	r = PsycoCode_Run(codebuf, f, what == PyTrace_CALL);
	f->f_tstate->tracing++;
	Py_DECREF(codebuf);
#if (PY_VERSION_HEX >= 0x02030000) && (PY_VERSION_HEX < 0x020300f0)
	if (!r) f->f_stacktop = NULL;  /* work around a bug in Python 2.3b1 */
#endif
	return r;
}


static int do_trace_or_profile(PyObject *v, PyFrameObject *frame,
			       int what, PyObject *arg)
{
	return !call_ceval_hooks((ceval_events_t*) v, what, frame);
}
static void extended_SetProfile(PyThreadState* tstate, Py_tracefunc func,
				PyObject* arg)
{
	/* cannot use PyEval_SetProfile() because it cannot set the
	   hook for another tstate than the current one */
	PyObject *temp = tstate->c_profileobj;
	Py_XINCREF(arg);
	tstate->c_profilefunc = NULL;
	tstate->c_profileobj = NULL;
	tstate->use_tracing = tstate->c_tracefunc != NULL;
	Py_XDECREF(temp);
	tstate->c_profilefunc = func;
	tstate->c_profileobj = arg;
	tstate->use_tracing = (func != NULL) || (tstate->c_tracefunc != NULL);
}
static void extended_SetTrace(PyThreadState* tstate, Py_tracefunc func,
			      PyObject* arg)
{
	/* cannot use PyEval_SetProfile() because it cannot set the
	   hook for another tstate than the current one */
	PyObject *temp = tstate->c_traceobj;
	Py_XINCREF(arg);
	tstate->c_tracefunc = NULL;
	tstate->c_traceobj = NULL;
	tstate->use_tracing = tstate->c_profilefunc != NULL;
	Py_XDECREF(temp);
	tstate->c_tracefunc = func;
	tstate->c_traceobj = arg;
	tstate->use_tracing = ((func != NULL)
			       || (tstate->c_profilefunc != NULL));
}
PSY_INLINE bool pstartprofile(PyThreadState* tstate)
{
	/* Set Python profile function to our function */
	if (tstate->c_profilefunc == NULL) {
		ceval_events_t* cev = get_cevents(tstate);
		extended_SetProfile(tstate, &do_trace_or_profile,
				    (PyObject*) cev);
	}
	return tstate->c_profilefunc == &do_trace_or_profile;
}
PSY_INLINE void pstopprofile(PyThreadState* tstate)
{
	if (tstate->c_profilefunc == &do_trace_or_profile) {
		extended_SetProfile(tstate, NULL, NULL);
	}
}
PSY_INLINE bool pstarttrace(PyThreadState* tstate)
{
	/* Set Python profile function to our function */
	if (tstate->c_tracefunc == NULL) {
		ceval_events_t* cev = get_cevents(tstate);
		extended_SetTrace(tstate, &do_trace_or_profile,
				  (PyObject*) cev);
	}
	return tstate->c_tracefunc == &do_trace_or_profile;
}
PSY_INLINE void pstoptrace(PyThreadState* tstate)
{
	if (tstate->c_tracefunc == &do_trace_or_profile) {
		extended_SetTrace(tstate, NULL, NULL);
	}
}


static bool update_ceval_hooks(ceval_events_t* cev)
{
	char needed;
	if (cev->events_total == 0) {
		needed = 0;
	}
	else if (cev->events[PyTrace_LINE].count == 0) {
		needed = 'P';  /* profile hook only, no line-by-line tracing */
	}
	else {
		needed = 'T';  /* line-by-line tracing hook */
	}
	if (cev->current_hook != needed) {
		PyThreadState* tstate = cev->tstate;
		switch (cev->current_hook) {
		case 'P':
			pstopprofile(tstate);
			break;
		case 'T':
			pstoptrace(tstate);
			break;
		}
		switch (needed) {
		case 'P':
			if (pstartprofile(tstate))
				break;  /* ok */
			needed = 'T';
			/* cannot use profile hook, try to fall through
			   to trace hook */
			debug_printf(1, ("profiler hooks busy, "
					 "trying with the slower trace hooks"));
		
		case 'T':
			if (pstarttrace(tstate))
				break;  /* ok */
			cev->current_hook = 0;
			stats_printf(("stats: update_ceval_hooks() cancel\n"));
			return false;
		}
		cev->current_hook = needed;
	}
	return true;
}


/***************************************************************/
 /***   Profiling all threads                                 ***/

typedef void (*profile_fn) (ceval_events_t*, int);
static profile_fn profile_function = NULL;

DEFINEFN
void psyco_profile_threads(int start)
{
	PyInterpreterState* istate;
	PyThreadState* tstate;
	
	if (!profile_function)
		return;
	istate = PyThreadState_Get()->interp;
	for (tstate=istate->tstate_head; tstate; tstate=tstate->next) {
		ceval_events_t* cev;
		if (!measuring_state(tstate))
			continue;
		cev = get_cevents(tstate);
		if (start == !cev->current_hook) {
			stats_printf(("stats: %s hooks on thread %p\n",
				      start?"adding":"removing", tstate));
			profile_function(cev, start);
			if (!update_ceval_hooks(cev) && start) {
				/* cannot start, stop again */
				profile_function(cev, 0);
			}
		}
	}
}

DEFINEFN bool psyco_set_profiler(void (*rs)(void*, int))
{
	if (rs == NULL) {
		psyco_profile_threads(0);
	}
	else {
		ceval_events_t* cev = get_cevents(PyThreadState_Get());
		profile_fn f = (profile_fn) rs;
		f(cev, 1);
		if (!update_ceval_hooks(cev)) {
			psyco_profile_threads(0);
			return false;
		}
		profile_function = f;
		psyco_profile_threads(1);
	}
	return true;
}


/***************************************************************/
 /***   Active profiling via Python's profiler hooks          ***/

static PyObject* profile_call(PyFrameObject* frame, PyObject* arg)
{
	PyCodeStats* cs;
	psyco_stats_append(frame->f_tstate, frame->f_back);

	cs = PyCodeStats_Get(frame->f_code);
	if (cs->st_globals != NULL) {
		/* we want to accelerate this code object */
		if (cs->st_codebuf == NULL) {
			/* not already compiled, compile it now */
			PyObject* g = frame->f_globals;
			int rec, module;
			stats_printf(("stats: compile code:  %s\n",
				      PyCodeObject_NAME(frame->f_code)));
			if (PyInt_Check(cs->st_globals))
				rec = PyInt_AS_LONG(cs->st_globals);
			else
				rec = DEFAULT_RECURSION;
			module = frame->f_globals == frame->f_locals;
			cs->st_codebuf = PsycoCode_CompileCode(frame->f_code,
							       g, rec, module);
			if (cs->st_codebuf == Py_None)
				g = NULL;  /* failed */
			else {
				Py_INCREF(g);
				extra_assert
					(CodeBuffer_Check(cs->st_codebuf));
			}
			Py_DECREF(cs->st_globals);
			cs->st_globals = g;
		}
		/* already compiled a Psyco version, run it
		   if the globals match */
		extra_assert(frame->f_globals != NULL);
		if (cs->st_globals == frame->f_globals) {
			Py_INCREF(cs->st_codebuf);
			return cs->st_codebuf;
		}
	}
	return NULL;
}

static PyObject* profile_return(PyFrameObject* frame, PyObject* arg)
{
	psyco_stats_append(frame->f_tstate, frame);
	return NULL;
}

DEFINEFN
void psyco_rs_profile(void* cev_raw, int start)
{
	ceval_events_t* cev = (ceval_events_t*) cev_raw;
	if (start) {
		set_ceval_hook(cev, PyTrace_CALL, &profile_call, NULL);
		set_ceval_hook(cev, PyTrace_RETURN, &profile_return, NULL);
	}
	else {
		unset_ceval_hook(cev, PyTrace_CALL, &profile_call, NULL);
		unset_ceval_hook(cev, PyTrace_RETURN, &profile_return, NULL);
	}
}


/***************************************************************/
 /***   Full compiling via Python's profiler hooks            ***/

static PyObject* do_fullcompile(PyFrameObject* frame, PyObject* arg)
{
	PyCodeStats* cs;
	cs = PyCodeStats_Get(frame->f_code);
	if (cs->st_codebuf == NULL) {
		/* not already compiled, compile it now */
		PyObject* g = frame->f_globals;
		int rec, module;
		stats_printf(("stats: full compile code:  %s\n",
			      PyCodeObject_NAME(frame->f_code)));
		if (cs->st_globals && PyInt_Check(cs->st_globals))
			rec = PyInt_AS_LONG(cs->st_globals);
		else
			rec = DEFAULT_RECURSION;
                module = frame->f_globals == frame->f_locals;
		cs->st_codebuf = PsycoCode_CompileCode(frame->f_code,
						       g, rec, module);
		if (cs->st_codebuf == Py_None)
			g = NULL;  /* failed */
		else {
			Py_INCREF(g);
			extra_assert(CodeBuffer_Check(cs->st_codebuf));
		}
		Py_XDECREF(cs->st_globals);
		cs->st_globals = g;
	}
	/* already compiled a Psyco version, run it if the globals match */
	extra_assert(frame->f_globals != NULL);
	if (cs->st_globals == frame->f_globals) {
		Py_INCREF(cs->st_codebuf);
		return cs->st_codebuf;
	}
	return NULL;
}

DEFINEFN
void psyco_rs_fullcompile(void* cev_raw, int start)
{
	ceval_events_t* cev = (ceval_events_t*) cev_raw;
	if (start) {
		set_ceval_hook(cev, PyTrace_CALL, &do_fullcompile, NULL);
	}
	else {
		unset_ceval_hook(cev, PyTrace_CALL, &do_fullcompile, NULL);
	}
}


/***************************************************************/
 /***   No compiling, but execution of already compiled code  ***/

static PyObject* do_nocompile(PyFrameObject* frame, PyObject* arg)
{
	PyCodeStats* cs;
	cs = PyCodeStats_MaybeGet(frame->f_code);
	/* if already compiled a Psyco version, run it if the globals match */
	if (cs != NULL && cs->st_codebuf != NULL &&
	    cs->st_globals == frame->f_globals) {
		extra_assert(frame->f_globals != NULL);
		Py_INCREF(cs->st_codebuf);
		return cs->st_codebuf;
	}
	return NULL;
}

DEFINEFN
void psyco_rs_nocompile(void* cev_raw, int start)
{
	ceval_events_t* cev = (ceval_events_t*) cev_raw;
	if (start) {
		set_ceval_hook(cev, PyTrace_CALL, &do_nocompile, NULL);
	}
	else {
		unset_ceval_hook(cev, PyTrace_CALL, &do_nocompile, NULL);
	}
}


/***************************************************************/
 /***   Turbo-ing a frame via Python's tracing hooks          ***/

/* Careful when changing the fields of a Python frame: ceval.c's
   interpreter will reload the changes and go on seamlessly only
   when hitting a line-trace step. */

static PyObject* turbo_wait(PyFrameObject* frame, PyObject* target_frame);

static PyObject* turbo_go(PyFrameObject* frame, PyObject* target_frame)
{
	PyObject* result;
	ceval_events_t* cev = get_cevents(frame->f_tstate);
	
	/* single-shooting callback */
	unset_ceval_hook(cev, PyTrace_LINE, &turbo_go, target_frame);
	
	if ((PyObject*) frame == target_frame) {
		/* the target is the current frame, compile it now */
		stats_printf(("stats: compile frame: %s\n",
			      PyCodeObject_NAME(frame->f_code)));
		result = PsycoCode_CompileFrame(frame, DEFAULT_RECURSION);
		if (result == Py_None) {
			Py_DECREF(result);
			result = NULL;
		}
	}
	else {
		/* hey, where is my frame? */
		PyFrameObject* f = frame->f_back;
		stats_printf(("stats: where is my frame?\n"));
		for (; f; f = f->f_back) {
			if ((PyObject*) f == target_frame) {
				/* it is lower in the stack, wait until
				   we return to it */
				stats_printf(("stats: lower in the stack.\n"));
				set_ceval_hook(cev, PyTrace_RETURN, &turbo_wait,
					       target_frame);
				break;
			}
		}
		/* if nowhere to be seen, forget it */
		result = NULL;
	}
	if (!update_ceval_hooks(cev))
		unset_ceval_hook(cev, PyTrace_RETURN, &turbo_wait, target_frame);
	return result;
}

static PyObject* turbo_wait(PyFrameObject* frame, PyObject* target_frame)
{
	if ((PyObject*)(frame->f_back) == target_frame) {
		/* here is my frame, we are returning back to it */
		ceval_events_t* cev = get_cevents(frame->f_tstate);
		unset_ceval_hook(cev, PyTrace_RETURN, &turbo_wait, target_frame);
		set_ceval_hook(cev, PyTrace_LINE, &turbo_go, target_frame);
		if (!update_ceval_hooks(cev))
			unset_ceval_hook(cev, PyTrace_LINE,
					 &turbo_go, target_frame);
	}
	return NULL;
}

DEFINEFN
bool psyco_turbo_frame(PyFrameObject* frame)
{
	if (frame->f_lasti >= 0) {
		/* turbo-run the frame at the next possible occasion
		   unless the frame is actually emulated from a Psyco frame */
		ceval_events_t* cev = get_cevents(frame->f_tstate);
		stats_printf(("stats: turbo frame: %s\n",
			      PyCodeObject_NAME(frame->f_code)));
/* 		if (frame->f_tstate != PyThreadState_GET()) { */
/* 			stats_printf(("stats: TSTATE = %p, F_TSTATE=%p\n", */
/* 				      PyThreadState_GET(), */
/* 				      frame->f_tstate)); */
/* 		} */
		set_ceval_hook(cev, PyTrace_LINE, &turbo_go, (PyObject*) frame);
		if (!update_ceval_hooks(cev)) {
			unset_ceval_hook(cev, PyTrace_LINE, &turbo_go,
					 (PyObject*) frame);
			return false;
		}
	}
	return true;
}

DEFINEFN
void psyco_turbo_code(PyCodeObject* code, int recursion)
{
	PyCodeStats* cs = PyCodeStats_Get(code);
	if (cs->st_codebuf == NULL && cs->st_globals == NULL) {
		/* trigger compilation at the next occasion
		   by storing something non-NULL in st_globals */
		cs->st_globals = PyInt_FromLong(recursion);
		if (cs->st_globals == NULL)
			OUT_OF_MEMORY();
        }
}

DEFINEFN
void psyco_turbo_frames(PyCodeObject* code)
{
	/* search all reachable Python frames
	   (this might overlook pending generators) */
	PyInterpreterState* istate = PyThreadState_Get()->interp;
	PyThreadState* tstate;
	for (tstate=istate->tstate_head; tstate; tstate=tstate->next) {
		PyFrameObject* f = tstate->frame;
		for (; f; f = f->f_back) {
			if (f->f_code == code)
				psyco_turbo_frame(f);
		}
	}
}


 /***************************************************************/

INITIALIZATIONFN
void psyco_profile_init(void)
{
	ceval_events_key = PyString_InternFromString("PsycoC");
}
