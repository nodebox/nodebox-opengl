#include "psyfunc.h"
#include "vcompiler.h"
#include "codemanager.h"
#include "mergepoints.h"
#include "stats.h"
#include "Objects/ptupleobject.h"
#include "Python/frames.h"
#include "Python/pycompiler.h"

#include <eval.h>  /* for PyEval_EvalCodeEx() */


 /***************************************************************/
/***   Frame and arguments building                            ***/
 /***************************************************************/

static void fix_run_time_args(PsycoObject * po, vinfo_array_t* target,
                              vinfo_array_t* source, RunTimeSource* sources)
{
  int i = target->count;
  extra_assert(target->count <= source->count);
  while (i--)
    {
      vinfo_t* a = source->items[i];
      if (a != NULL && a->tmp != NULL)
        {
          vinfo_t* b = a->tmp;
          if (is_runtime(a->source))
            {
              if (target->items[i] == NULL)
                continue;  /* item was removed by psyco_simplify_array() */
              if (sources != NULL) {
                int argc = (po->stack_depth-INITIAL_STACK_DEPTH) / sizeof(long);
                sources[argc] = a->source;
              }
              po->stack_depth += sizeof(long);
              /* arguments get borrowed references */
              b->source = RunTime_NewStack(po->stack_depth, false, false);
            }
          extra_assert(b == target->items[i]);
          a->tmp = NULL;
          if (a->array != NullArray)
            fix_run_time_args(po, b->array, a->array, sources);
        }
    }
}

struct fncall_arg_s {
  PyCodeObject* co;
  PyObject* merge_points;
  vinfo_array_t* inputvinfos;
  int po_size;
};

static bool fncall_init(struct fncall_arg_s* fncall,
                        PyCodeObject* co)
{
  int ncells = PyTuple_GET_SIZE(co->co_cellvars);
  int nfrees = PyTuple_GET_SIZE(co->co_freevars);
  if (co->co_flags & CO_VARKEYWORDS)
    {
      debug_printf(1, ("unsupported ** argument in call to %s\n",
                       PyCodeObject_NAME(co)));
      return false;
    }
  if (ncells != 0 || nfrees != 0)
    {
      debug_printf(1, ("unsupported free or cell vars in %s\n",
                       PyCodeObject_NAME(co)));
      return false;
    }
  fncall->co = co;
  fncall->merge_points = psyco_get_merge_points(co, 0);
  return fncall->merge_points != Py_None;
}

static bool fncall_collect_arguments(struct fncall_arg_s* fncall,
                                     vinfo_t* vglobals,
                                     vinfo_t** argarray, int argcount,
                                     vinfo_t** defarray, int defcount)
{
  PyCodeObject* co = fncall->co;
  vinfo_array_t* inputvinfos;
  int i, minargcnt, inputargs, extras;

  minargcnt = co->co_argcount - defcount;
  inputargs = argcount;
  if (inputargs != co->co_argcount)
    {
      if (inputargs > co->co_argcount && (co->co_flags & CO_VARARGS))
        /* ok, extra args will be collected below */ ;
      else
        {
          if (inputargs < minargcnt || inputargs > co->co_argcount)
            {
              int n = co->co_argcount < minargcnt ? minargcnt : co->co_argcount;
              PyErr_Format(PyExc_TypeError,
                           "%.200s() takes %s %d %sargument%s (%d given)",
                           PyCodeObject_NAME(co),
                           minargcnt == co->co_argcount ? "exactly" :
                           (inputargs < n ? "at least" : "at most"),
                           n,
                           /*kwcount ? "non-keyword " :*/ "",
                           n == 1 ? "" : "s",
                           inputargs);
              return false;
            }
          inputargs = co->co_argcount;  /* add default arguments */
        }
    }

  /* Collect all input vinfo_t's (globals, arguments, needed default values)
     into a new array that mimics the PsycoObject's vlocals. */
  inputvinfos = array_new(INDEX_LOC_LOCALS_PLUS + inputargs);
  inputvinfos->items[INDEX_LOC_GLOBALS] = vglobals;
  for (i=0; i<argcount; i++)
    inputvinfos->items[INDEX_LOC_LOCALS_PLUS+i] = argarray[i];
  for (; i<inputargs; i++)
    inputvinfos->items[INDEX_LOC_LOCALS_PLUS+i] = defarray[i-minargcnt];

  extras = co->co_stacksize + co->co_nlocals; /*+ncells+nfrees, both 0 now */
  fncall->inputvinfos = inputvinfos;
  fncall->po_size     = INDEX_LOC_LOCALS_PLUS + extras;
  return true;
}

PSY_INLINE void fncall_finish_store(struct fncall_arg_s* fncall,
                                PsycoObject* po)
{
  array_release(fncall->inputvinfos);
  
  /* store the code object */
  po->pr.co = fncall->co;
  Py_INCREF(fncall->co);  /* XXX never freed */
  pyc_data_build(po, fncall->merge_points);
}

static void fncall_store_arguments(struct fncall_arg_s* fncall,
                                   vinfo_t** vlocals)
{
  PyCodeObject* co = fncall->co;
  vinfo_array_t* arraycopy = fncall->inputvinfos;
  vinfo_t** pp;
  int i;
  int inputargs = arraycopy->count - INDEX_LOC_LOCALS_PLUS;
  
  /* initialize po->vlocals */
  vlocals[INDEX_LOC_GLOBALS] = arraycopy->items[INDEX_LOC_GLOBALS];

  /* move the arguments into their target place,
     excluding the ones that map to the '*' parameter */
  pp = arraycopy->items + INDEX_LOC_LOCALS_PLUS;
  for (i=0; i<co->co_argcount; i++)
    vlocals[INDEX_LOC_LOCALS_PLUS + i] = *pp++;
  if (co->co_flags & CO_VARARGS)
    {
      /* store the extra args in a virtual-time tuple */
      vlocals[INDEX_LOC_LOCALS_PLUS + i] = PsycoTuple_New(inputargs - i, pp);
      for (; inputargs > i; inputargs--)
        vinfo_decref(*pp++, NULL);
      i++;
    }
  else
    extra_assert(i == inputargs);

  /* the rest of locals is uninitialized */
  for (; i<co->co_nlocals; i++)
    vlocals[INDEX_LOC_LOCALS_PLUS + i] = psyco_vi_Zero();
  /* the rest of the array is the currently empty stack,
     set to NULL by array_new(). */
}

/* Build a PsycoObject "frame" corresponding to the call of a Python
   function.  If 'sources!=NULL', it is set to an array of the sources of
   the values that must be pushed to make the call. */
static PsycoObject* psyco_build_frame(struct fncall_arg_s* fncall,
                                      int recursion, RunTimeSource** sources)
{
  /* build a "frame" in a PsycoObject according to the given code object. */
  vinfo_array_t* arraycopy;
  PsycoObject* po;
  int rtcount;
  RunTimeSource* source1;
  
  po = PsycoObject_New(fncall->po_size);
  po->stack_depth = INITIAL_STACK_DEPTH;
  po->vlocals.count = fncall->po_size;
  INIT_PROCESSOR_PSYCOOBJECT(po);
  po->pr.auto_recursion = AUTO_RECURSION(recursion);

  /* duplicate the inputvinfos. If two arguments share some common part, they
     will also share it in the copy. */
  clear_tmp_marks(fncall->inputvinfos);
  arraycopy = array_new(fncall->inputvinfos->count);
  duplicate_array(arraycopy, fncall->inputvinfos);

  /* simplify arraycopy in the sense of psyco_simplify_array() */
  rtcount = psyco_simplify_array(arraycopy, NULL);

  /* all run-time arguments or argument parts must be corrected: in the
     input vinfo_t's they have arbitrary sources, but in the new frame's
     sources they will have to be fetched from the machine stack, where
     the caller will have pushed them. */
  if (sources != NULL)
    {
      source1 = PyMem_NEW(RunTimeSource, rtcount);
      if (source1 == NULL && rtcount > 0)
        OUT_OF_MEMORY();
      *sources = source1;
    }
  else
    source1 = NULL;
  fix_run_time_args(po, arraycopy, fncall->inputvinfos, source1);
  array_release(fncall->inputvinfos);
  fncall->inputvinfos = arraycopy;

  /* initialize po->vlocals */
  fncall_store_arguments(fncall, po->vlocals.items);
  fncall_finish_store(fncall, po);

  /* set up the CALL return address */
  po->stack_depth += sizeof(long);
  LOC_CONTINUATION = vinfo_new(RunTime_NewStack(po->stack_depth, false, false));
  return po;
}

/* extra data that must be saved about a parent frame when a child
   frame is about to be run in-line in the same PsycoObject */
#define LOC_INLINE_CO           0
#define LOC_INLINE_NEXT_INSTR   1
#define TOTAL_LOC_INLINE        2

static vinfo_t* call_with_inline_frame(PsycoObject* po,
                                       struct fncall_arg_s* fncall,
                                       int recursion)
{
  /* note: 'recursion' is ignored */
  vinfo_t* vresult;
  if (LOC_INLINING != NULL)   /* we have the result ready from the
                                 initial case below */
    {
      vresult = LOC_INLINING;
      LOC_INLINING = NULL;
    }
  else
    {
      /* initial case: collect the arguments from the call into an
         EInline pseudo-exception */
      int i;
      vinfo_t** pp = fncall->inputvinfos->items;
      vinfo_t* v = vinfo_new(SOURCE_NOT_IMPORTANT);
      v->array = array_new(TOTAL_LOC_INLINE + fncall->po_size);
      v->array->items[LOC_INLINE_CO] =
        vinfo_new(CompileTime_New((long) fncall->co));
      Py_INCREF(fncall->co);  /* XXX never freed */
      for (i=fncall->inputvinfos->count; i--; )
        if (pp[i] != NULL)
          vinfo_incref(pp[i]);
      fncall_store_arguments(fncall, v->array->items + TOTAL_LOC_INLINE);
      PycException_Raise(po, vinfo_new(VirtualTime_New(&EInline)), v);
      vresult = NULL;
    }
  array_release(fncall->inputvinfos);
  return vresult;
}

DEFINEFN
vinfo_t* psyco_save_inline_po(PsycoObject* po)
{
  int i = po->vlocals.count;
  vinfo_t** pp = po->vlocals.items;
  vinfo_t* v = vinfo_new(VirtualTime_New(&EInline));
  v->array = array_new(TOTAL_LOC_INLINE + i);
  v->array->items[LOC_INLINE_CO] =
    vinfo_new(CompileTime_New((long) po->pr.co));
  v->array->items[LOC_INLINE_NEXT_INSTR] =
    vinfo_new(CompileTime_New(po->pr.next_instr));
  while (i--)
    {
      v->array->items[TOTAL_LOC_INLINE + i] = pp[i];
      pp[i] = NULL;
    }
  return v;
}

DEFINEFN
PsycoObject* psyco_restore_inline_po(PsycoObject* po, vinfo_array_t** a)
{
  int i;
  vinfo_t* v;
  vinfo_array_t* array = *a;
  *a = NullArray;

  for (i=po->vlocals.count; i--; )
    vinfo_xdecref(po->vlocals.items[i], po);
  i = array->count - TOTAL_LOC_INLINE;
  po = PsycoObject_Resize(po, i);
  po->vlocals.count = i;  /* attention, vlocals.count cannot be larger than i
                             even if there is enough memory already allocated */
  while (i--)
    po->vlocals.items[i] = array->items[TOTAL_LOC_INLINE + i];

  v = array->items[LOC_INLINE_CO];
  po->pr.co = (PyCodeObject*) CompileTime_Get(v->source)->value;
  vinfo_decref(v, NULL);
  v = array->items[LOC_INLINE_NEXT_INSTR];
  po->pr.next_instr = v ? CompileTime_Get(v->source)->value : 0;
  vinfo_xdecref(v, NULL);
  array_release(array);

  pyc_data_build(po, psyco_get_merge_points(po->pr.co, -1));
  po->pr.f_builtins = NULL;  /* because the globals might have changed */
  return po;
}


static PyObject* cimpl_call_pyfunc(PyCodeObject* co, PyObject* globals,
                                   PyObject* defaults, PyObject* arg)
{
  /* simple wrapper around PyEval_EvalCodeEx, for the fail_to_default
     case of psyco_call_pyfunc() */
  int defcount = (defaults ? PyTuple_GET_SIZE(defaults) : 0);
  PyObject** defs = (defcount ? &PyTuple_GET_ITEM(defaults, 0) : NULL);
  return PyEval_EvalCodeEx(co, globals, (PyObject*)NULL,
                           &PyTuple_GET_ITEM(arg, 0), PyTuple_GET_SIZE(arg),
                           (PyObject**)NULL, 0,
                           defs, defcount, NULL);
}

#define COMPUTE_DEFCOUNT()    do {                              \
  /* is vdefaults!=NULL at run-time ? */                        \
  condition_code_t cc = object_non_null(po, vdefaults);         \
  if (cc == CC_ERROR)  /* error or more likely promotion */     \
    return NULL;                                                \
  if (runtime_condition_t(po, cc))                              \
    defcount = PsycoTuple_Load(vdefaults);                      \
  else                                                          \
    defcount = 0;  /* vdefaults==NULL at run-time */            \
} while (0)

DEFINEFN
vinfo_t* psyco_call_pyfunc(PsycoObject* po, PyCodeObject* co,
                           vinfo_t* vglobals, vinfo_t* vdefaults,
                           vinfo_t* arg_tuple, int recursion)
{
  CodeBufferObject* codebuf;
  PsycoObject* mypo;
  Source* sources;
  vinfo_t* result;
  stack_frame_info_t* finfo;
  int tuple_size, argcount, defcount=-2;
  struct fncall_arg_s fncall;

  if (is_proxycode(co))
    {
      PsycoFunctionObject* pf;
      pf = (PsycoFunctionObject*) PyTuple_GET_ITEM(co->co_consts, 1);
      co = pf->psy_code;
      if (pf->psy_defaults == NULL)
        vdefaults = PsycoTuple_New(0, NULL);
      else
        {
          Py_INCREF(pf->psy_defaults);  /* XXX looses a ref */
          vdefaults = vinfo_new(
              CompileTime_NewSk(sk_new((long) pf->psy_defaults,
                                       SkFlagPyObj)));
        }
      /* the recursion limit only applies to non-proxified functions */
      recursion++;
      result = psyco_call_pyfunc(po, co, vglobals, vdefaults,
                                 arg_tuple, recursion);
      vinfo_decref(vdefaults, po);
      return result;
    }
  if (--recursion < 0)
    goto fail_to_default;
  extra_assert(PyCode_GetNumFree(co) == 0);
  
  tuple_size = PsycoTuple_Load(arg_tuple);
  if (tuple_size == -1)
    goto fail_to_default;
      /* XXX calling with an unknown-at-compile-time number of arguments
         is not implemented, revert to the default behaviour */

  COMPUTE_DEFCOUNT();
  if (defcount == -1)
    goto fail_to_default;
  /* calling with an unknown-at-compile-time number of default arguments
     is not implemented (but this is probably not useful to implement);
     revert to the default behaviour */

  /* Force mutable arguments out of virtual-time,
     including the processor condition codes */
  /* This is expected to have already been done on default arguments;
     see PsycoFunction_New() */
  if (!psyco_forking(po, arg_tuple->array))
    return NULL;
  
  /* prepare a frame */
  if (!fncall_init(&fncall, co))
    goto fail_to_default;  /* unsupported bytecode features */
  if (!fncall_collect_arguments(&fncall, vglobals,
                                &PsycoTuple_GET_ITEM(arg_tuple, 0), tuple_size,
                                &PsycoTuple_GET_ITEM(vdefaults, 0), defcount))
    goto pyerr;  /* Python exception (wrong # of arguments) */

  /* try to inline the call */
  if (!po->pr.is_inlining &&
      (psyco_mp_flags(fncall.merge_points) & MP_FLAGS_INLINABLE))
    {
      /* inlining call */
      result = call_with_inline_frame(po, &fncall, recursion);
    }
  else
    {
      /* non-inlining call */
      mypo = psyco_build_frame(&fncall, recursion, &sources);
      if (mypo == NULL)
        goto pyerr;
      argcount = get_arguments_count(&mypo->vlocals);
      finfo = psyco_finfo(po, mypo);

      /* compile the function (this frees mypo) */
      codebuf = psyco_compile_code(mypo, PsycoObject_Ready(mypo));

      /* get the run-time argument sources and push them on the stack
         and write the actual CALL */
      result = psyco_call_psyco(po, codebuf, sources, argcount, finfo);
      PyMem_FREE(sources);
    }
  return result;

 fail_to_default:
  return psyco_generic_call(po, cimpl_call_pyfunc,
                            CfReturnRef|CfPyErrIfNull,
                            "lvvv", co, vglobals, vdefaults, arg_tuple);

 pyerr:
  psyco_virtualize_exception(po);
  return NULL;
}


 /***************************************************************/
/***   PsycoFunctionObjects                                    ***/
 /***************************************************************/

DEFINEFN
PsycoFunctionObject* psyco_PsycoFunction_NewEx(PyCodeObject* code,
					       PyObject* globals,
					       PyObject* defaults,
					       int rec)
{
	PsycoFunctionObject* result = PyObject_GC_New(PsycoFunctionObject,
						      &PsycoFunction_Type);
	if (result != NULL) {
		result->psy_code = code;         Py_INCREF(code);
		result->psy_globals = globals;   Py_INCREF(globals);
		result->psy_defaults = NULL;
		result->psy_recursion = rec;
		result->psy_fastcall = PyList_New(0);
		PyObject_GC_Track(result);

		if (result->psy_fastcall == NULL) {
			Py_DECREF(result);
			return NULL;
		}

		if (defaults != NULL) {
			if (!PyTuple_Check(defaults)) {
				Py_DECREF(result);
				PyErr_SetString(PyExc_PsycoError,
						"Psyco proxies need a tuple "
						"for default arguments");
				return NULL;
			}
			if (PyTuple_GET_SIZE(defaults) > 0) {
				result->psy_defaults = defaults;
				Py_INCREF(defaults);
			}
		}
	}
	return result;
}

#if 0  /* unneeded */
DEFINEFN
PyObject* psyco_PsycoFunction_New(PyFunctionObject* func, int rec)
{
	/* return 'func' itself if the PsycoFunctionObject cannot be made */
	if (func->func_closure != NULL) {
		Py_INCREF(func);
		return (PyObject*) func;
	}
	return (PyObject*)
		psyco_PsycoFunction_NewEx((PyCodeObject*) func->func_code,
					  func->func_globals,
					  func->func_defaults,
					  rec);
}
#endif  /* 0 */

DEFINEFN
PyObject* psyco_proxycode(PyFunctionObject* func, int rec)
{
  PsycoFunctionObject *psyco_fun;
  PyCodeObject *code, *newcode;
  PyObject *consts, *proxy_cobj;
  static PyObject *varnames = NULL;
  static PyObject *free_cell_vars = NULL;
  static PyObject *empty_string = NULL;
  unsigned char proxy_bytecode[] = {
    LOAD_CONST, 1, 0,
    LOAD_FAST, 0, 0,
    LOAD_FAST, 1, 0,
    CALL_FUNCTION_VAR_KW, 0, 0,
    RETURN_VALUE
  };
  code = (PyCodeObject *)func->func_code;
  if (is_proxycode(code))
    {
      /* already a proxy code object */
      Py_INCREF(code);
      return (PyObject*) code;
    }
  if (PyCode_GetNumFree(code) > 0)
    {
      /* it would be dangerous to continue in this case: the calling
         convention changes when a function has free variables */
      PyErr_SetString(PyExc_PsycoError, "function has free variables");
      return NULL;
    }

  newcode = NULL;
  consts = NULL;
  proxy_cobj = NULL;
  psyco_fun = psyco_PsycoFunction_NewEx(code,
					func->func_globals,
					func->func_defaults,
					rec);
  if (psyco_fun == NULL)
    goto error;

  consts = PyTuple_New(2);
  if (consts == NULL)
    goto error;
  Py_INCREF(Py_None);
  PyTuple_SET_ITEM(consts, 0, Py_None);  /* if a __doc__ is expected there */
  PyTuple_SET_ITEM(consts, 1, (PyObject *)psyco_fun);  /* consumes reference */
  psyco_fun = NULL;

  if (varnames == NULL)
    {
      if (free_cell_vars == NULL)
        {
          free_cell_vars = PyTuple_New(0);
          if (free_cell_vars == NULL)
            goto error;
        }
      if (empty_string == NULL)
        {
          empty_string = PyString_FromString("");
          if (empty_string == NULL)
            goto error;
        }
      varnames = Py_BuildValue("ss", "args", "kwargs");
      if (varnames == NULL)
        goto error;
    }

  proxy_cobj = PyString_FromStringAndSize((char*)proxy_bytecode,
					  sizeof(proxy_bytecode));
  if (proxy_cobj == NULL)
    goto error;

  newcode = PyCode_New(0, 2, 3,
                       CO_OPTIMIZED|CO_NEWLOCALS|CO_VARARGS|CO_VARKEYWORDS,
                       proxy_cobj, consts,
		       varnames, varnames, free_cell_vars,
		       free_cell_vars, code->co_filename,
		       code->co_name, code->co_firstlineno,
		       empty_string);
  /* fall through */
 error:
  Py_XDECREF(psyco_fun);
  Py_XDECREF(proxy_cobj);
  Py_XDECREF(consts);
  return (PyObject*) newcode;
}

static void psycofunction_dealloc(PsycoFunctionObject* self)
{
	PyObject_GC_UnTrack(self);
	Py_XDECREF(self->psy_fastcall);
	Py_XDECREF(self->psy_defaults);
	Py_DECREF(self->psy_globals);
	Py_DECREF(self->psy_code);
	PyObject_GC_Del(self);
}

#if 0
/* Disabled -- not supposed to be seen at user level */
static PyObject* psycofunction_repr(PsycoFunctionObject* self)
{
	char buf[100];
	if (self->psy_func->func_name == Py_None)
		sprintf(buf, "<anonymous psyco function at %p>", self);
	else
		sprintf(buf, "<psyco function %s at %p>",
			PyString_AsString(self->psy_func->func_name), self);
	return PyString_FromString(buf);
}
#endif

static PyObject* psycofunction_call(PsycoFunctionObject* self,
				    PyObject* arg, PyObject* kw)
{
	PyObject* codebuf;
	PyObject* result;
	PyObject* tdict;
	PyFrameRuntime* fruntime;
	PyObject* f;
	stack_frame_info_t** finfo;
        long* initial_stack;
	int key;
	bool err;

	if (kw != NULL && PyDict_Check(kw) && PyDict_Size(kw) > 0) {
		/* keyword arguments not supported yet */
		goto unsupported;
	}

	key = PyTuple_GET_SIZE(arg);
	if (key < PyList_GET_SIZE(self->psy_fastcall))
		codebuf = PyList_GET_ITEM(self->psy_fastcall, key);
        else
		codebuf = NULL;
	
	if (codebuf == NULL) {
		/* not already seen with this number of arguments */
		vinfo_t* vglobals;
		vinfo_array_t* vdefaults;
		vinfo_array_t* arginfo;
		PsycoObject* po = NULL;
		source_known_t* sk;
		struct fncall_arg_s fncall;
		bool support;
		int i = key;

		/* make an array of run-time values */
		arginfo = array_new(i);
		while (i--) {
			/* arbitrary values for the source */
			arginfo->items[i] = vinfo_new(SOURCE_DUMMY);
		}

		/* build the globals and defaults as compile-time values */
		Py_INCREF(self->psy_globals);
		sk = sk_new((long) self->psy_globals, SkFlagPyObj);
		vglobals = vinfo_new(CompileTime_NewSk(sk));
		
		if (self->psy_defaults == NULL)
			vdefaults = NullArray;
		else {
			i = PyTuple_GET_SIZE(self->psy_defaults);
			vdefaults = array_new(i);
			while (i--) {
				PyObject* v = PyTuple_GET_ITEM(
							self->psy_defaults, i);
				Py_INCREF(v);
				sk = sk_new((long) v, SkFlagPyObj);
				vdefaults->items[i] =
					vinfo_new(CompileTime_NewSk(sk));
			}
		}
		
		/* make a "frame" */
		support = fncall_init(&fncall, self->psy_code);
		if (support && fncall_collect_arguments(&fncall, vglobals,
					arginfo->items, arginfo->count,
					vdefaults->items, vdefaults->count)) {
			po = psyco_build_frame(&fncall,
					       self->psy_recursion, NULL);
		}
		array_delete(vdefaults, NULL);
		vinfo_decref(vglobals, NULL);
		array_delete(arginfo, NULL);

		if (po == NULL) {
			if (!support) {
				/* unsupported bytecode features */
				codebuf = Py_None;
				Py_INCREF(codebuf);
			}
			else    /* Python exception (wrong # of arguments) */
				return NULL;
		}
		else {
			/* compile the function */
			codebuf = (PyObject*) psyco_compile_code(po,
						PsycoObject_Ready(po));
		}
		/* cache 'codebuf' (note that this is not necessary, as
		   multiple calls to psyco_compile_code() will just return
		   the same codebuf, but it makes things faster because we
		   don't have to build a whole PsycoObject the next time. */
		i = key+1 - PyList_GET_SIZE(self->psy_fastcall);
		if (i > 0) {
			/* list too short, first enlarge it with NULLs */
			PyObject* tmp = PyList_New(i);
			if (tmp != NULL) {
				PyList_SetSlice(self->psy_fastcall,
					PyList_GET_SIZE(self->psy_fastcall),
					PyList_GET_SIZE(self->psy_fastcall),
					tmp);
				Py_DECREF(tmp);
			}
			/* errors are detected by the failing PyList_SetItem()
			   call below */
		}
                /* Eats a reference to codebuf */
		if (PyList_SetItem(self->psy_fastcall, key, codebuf))
			PyErr_Clear();  /* not fatal, ignore error */
	}

	if (codebuf == Py_None)
		goto unsupported;

	/* over the current Python frame, a lightweight chained list of
	   Psyco frames will be built. Mark the current Python frame as
	   the starting point of this chained list. */
	f = (PyObject*) PyEval_GetFrame();
	if (f == NULL) {
		debug_printf(1, ("warning: empty Python frame stack\n"));
		goto unsupported;
	}
	tdict = psyco_thread_dict();
	if (tdict==NULL) return NULL;
	fruntime = PyCStruct_NEW(PyFrameRuntime, PyFrameRuntime_dealloc);
        Py_INCREF(f);
        fruntime->cs_key = f;
        fruntime->psy_frames_start = &finfo;
        fruntime->psy_code = self->psy_code;
        fruntime->psy_globals = self->psy_globals;
	extra_assert(PyDict_GetItem(tdict, f) == NULL);
	err = PyDict_SetItem(tdict, f, (PyObject*) fruntime);
	Py_DECREF(fruntime);
	if (err) return NULL;
	/* Warning, no 'return' between this point and the PyDict_DelItem()
	   below */
        
	/* get the actual arguments */
	extra_assert(RUN_ARGC(codebuf) == PyTuple_GET_SIZE(arg));
	initial_stack = (long*) (&PyTuple_GET_ITEM(arg, 0));

	/* run! */
	Py_INCREF(codebuf);
	result = psyco_processor_run((CodeBufferObject*) codebuf,
                                     initial_stack, &finfo, tdict);
	Py_DECREF(codebuf);
	psyco_trash_object(NULL);  /* free any trashed object now */

#if CODE_DUMP >= 2
        psyco_dump_code_buffers();
#endif
	if (PyDict_DelItem(tdict, f)) {
		Py_XDECREF(result);
		result = NULL;
	}

	if (result==NULL)
		extra_assert(PyErr_Occurred());
	else
		extra_assert(!PyErr_Occurred());
	return result;

   unsupported:
	{	/* Code copied from function_call() in funcobject.c */
		PyObject **d, **k;
		int nk, nd;

		PyObject* argdefs = self->psy_defaults;
		if (argdefs != NULL) {
			d = &PyTuple_GET_ITEM((PyTupleObject *)argdefs, 0);
			nd = PyTuple_Size(argdefs);
		}
		else {
			d = NULL;
			nd = 0;
		}

		if (kw != NULL && PyDict_Check(kw)) {
			int pos, i;
			nk = PyDict_Size(kw);
			k = PyMem_NEW(PyObject *, 2*nk);
			if (k == NULL) {
				PyErr_NoMemory();
				return NULL;
			}
			pos = i = 0;
			while (PyDict_Next(kw, &pos, &k[i], &k[i+1]))
				i += 2;
			nk = i/2;
		}
		else {
			k = NULL;
			nk = 0;
		}
		
		result = PyEval_EvalCodeEx(self->psy_code,
			self->psy_globals, (PyObject *)NULL,
			&PyTuple_GET_ITEM(arg, 0), PyTuple_Size(arg),
			k, nk, d, nd,
			NULL);

		if (k != NULL)
			PyMem_DEL(k);

		return result;
	}
}

static int psycofunction_traverse(PsycoFunctionObject *f,
				  visitproc visit, void *arg)
{
	int err;
	if (f->psy_fastcall) {
		err = visit(f->psy_fastcall, arg);
		if (err)
			return err;
	}
	if (f->psy_defaults) {
		err = visit(f->psy_defaults, arg);
		if (err)
			return err;
	}
	err = visit(f->psy_globals, arg);
	if (err)
		return err;
	return 0;
}

static int psycofunction_clear(PsycoFunctionObject *f)
{
	PyObject* o;
	o = f->psy_fastcall;
	if (o) {
		f->psy_fastcall = NULL;
		Py_DECREF(o);
	}
	o = f->psy_defaults;
	if (o) {
		f->psy_defaults = NULL;
		Py_DECREF(o);
	}
	o = f->psy_globals;
	f->psy_globals = Py_None;
	Py_INCREF(Py_None);
	Py_DECREF(o);
	return 0;
}

DEFINEVAR
PyTypeObject PsycoFunction_Type = {
	PyObject_HEAD_INIT(NULL)
	0,					/*ob_size*/
	"Psyco_function",			/*tp_name*/
	sizeof(PsycoFunctionObject),		/*tp_basicsize*/
	0,					/*tp_itemsize*/
	/* methods */
	(destructor)psycofunction_dealloc,	/*tp_dealloc*/
	0,					/*tp_print*/
	0,					/*tp_getattr*/
	0,					/*tp_setattr*/
	0,					/*tp_compare*/
	0,					/*tp_repr*/
	0,					/*tp_as_number*/
	0,					/*tp_as_sequence*/
	0,					/*tp_as_mapping*/
	0,					/*tp_hash*/
	(ternaryfunc)psycofunction_call,	/*tp_call*/
	0,					/* tp_str */
	0,					/* tp_getattro */
	0,					/* tp_setattro */
	0,					/* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,/* tp_flags */
	0,					/* tp_doc */
	(traverseproc)psycofunction_traverse,	/* tp_traverse */
	(inquiry)psycofunction_clear,		/* tp_clear */
};
