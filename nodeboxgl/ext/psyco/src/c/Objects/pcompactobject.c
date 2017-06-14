#include "compactobject.h"
#include "pcompactobject.h"
#include "../Python/pycompiler.h"
#include "ptupleobject.h"
#include "ptypeobject.h"

#define COMPACT_impl  FMUT(DEF_FIELD(PyCompactObject, compact_impl_t*, \
							k_impl, OB_type))
#define COMPACT_data  FMUT(DEF_FIELD(PyCompactObject, char*,           \
							k_data, COMPACT_impl))
#define iCOMPACT_IMPL  FIELD_INDEX(COMPACT_impl)
#define iCOMPACT_DATA  FIELD_INDEX(COMPACT_data)
#define COMPACT_TOTAL  FIELDS_TOTAL(COMPACT_data)

#define KDATA_AS_LONG   FMUT(DEF_ARRAY(long, 0))
#define KDATA_AS_PYOBJ  FMUT(FPYREF(DEF_ARRAY(PyObject*, 0)))
#define KDATA_AS_PYOBJ_NOREF   FMUT(DEF_ARRAY(PyObject*, 0))


#define PSY_READ_K_DATA(vdata, on_error)  do {				\
		if (vdata == NULL) {					\
			/* read ko->k_data */				\
			vdata = psyco_get_field(po, vk, COMPACT_data);	\
			if (vdata == NULL)				\
				on_error;				\
		}							\
	} while (0)


 /***************************************************************/
  /*** Meta-implementation of compact_getattro                 ***/

static vinfo_t* psy_k_load_vinfo(PsycoObject* po, vinfo_t* vsrc, vinfo_t* vk,
				 vinfo_t** pvdata)
{
	/* duplicate a vinfo_t structure from a compact_impl_t, generating
	   the code to read it out of the PyCompactObject */
	int sindex;
	vinfo_t* vresult;
	switch (gettime(vsrc->source)) {

	case RunTime:   /* read from the object's k_data */
		PSY_READ_K_DATA(*pvdata, return NULL);
		sindex = getstack(vsrc->source);
		if (has_rtref(vsrc->source)) {
			vresult = psyco_get_nth_field(po, *pvdata,
				KDATA_AS_PYOBJ, sindex / sizeof(PyObject*));
		}
		else {
			vresult = psyco_get_nth_field(po, *pvdata,
				KDATA_AS_LONG, sindex / sizeof(long));
		}
		if (!vresult)
			return NULL;
		break;

	case CompileTime:   /* return a fresh copy of the vinfo_t */
		sk_incref(CompileTime_Get(vsrc->source));
		return vinfo_new(vsrc->source);

	default:
		vresult = vinfo_new(vsrc->source);
	}
	if (vsrc->array != NullArray) {
		int i = vsrc->array->count;
		vinfo_array_grow(vresult, i);
		while (--i >= 0) {
			if (vsrc->array->items[i] != NULL) {
				vinfo_t* v;
				v = psy_k_load_vinfo(po, vsrc->array->items[i],
						     vk, pvdata);
				if (v == NULL) {
					vinfo_decref(vresult, po);
					return NULL;
				}
				vresult->array->items[i] = v;
			}
		}
	}
	return vresult;
}

struct source_tmp_virtual_s {
	source_virtual_t sv;
	PyObject* ko;
};

static struct source_tmp_virtual_s* stv_table_start = NULL;
static struct source_tmp_virtual_s* stv_table_next = NULL;
static struct source_tmp_virtual_s* stv_table_stop = NULL;

static bool compute_stv_never(PsycoObject* po, vinfo_t* vk)
{
	psyco_fatal_msg("compute_stv_never");
	return true;
}

PSY_INLINE struct source_tmp_virtual_s* malloc_stv(PyObject* ko)
{
	/* this leaks, but we try to minimize the impact by alloc'ing
	   blocks and doing some sharing */
	struct source_tmp_virtual_s* p;
	for (p = stv_table_start; p != stv_table_next; p++) {
		if (p->ko == ko)
			return p;
	}
	if (p == stv_table_stop) {
		p = (struct source_tmp_virtual_s*) malloc(
			64 * sizeof(struct source_tmp_virtual_s*));
		if (!p)
			OUT_OF_MEMORY();
		stv_table_start = p;
		stv_table_stop = p + 64;
	}
	INIT_SVIRTUAL_NOCALL(p->sv, compute_stv_never, 0);
	p->ko = ko;
	stv_table_next = p + 1;
	return p;
}

static compact_impl_t* pcompact_getimpl(PsycoObject* po, vinfo_t* vk)
{
	/* The problem is to promote the vimpl read out of vk.
	   To be promotable it must be temporarily stored in vk->array.
	   However, we cannot store a run-time vimpl in a compile-time vk.
	   Ideally, this restriction should be lifted, but this
	   would need a careful review of a lot of code and a lot
	   of testing :-(
	   Instead, this is done by temporarily turning the compile-time
	   vk into a virtual-time value. */

	long l;
	vinfo_t* vimpl;
	struct source_tmp_virtual_s* stv;
	vinfo_t* vtype;
	source_known_t* sk;

	vimpl = vinfo_getitem(vk, iCOMPACT_IMPL);
	if (vimpl == NULL) {
		/* initial case */
		vimpl = psyco_get_field(po, vk, COMPACT_impl);
		if (vimpl == NULL)
			return NULL;
		extra_assert(is_runtime(vimpl->source));  /* freshly read */
		if (is_compiletime(vk->source)) {
			/* CompileTime -> VirtualTime */
			/* leaks stv. */
			sk = CompileTime_Get(vk->source);
			stv = malloc_stv((PyObject*) sk->value);
			sk_decref(sk);
			vk->source = VirtualTime_New(&stv->sv);

			/* store the type as a constant in vk->array */
			vtype = vinfo_new(CompileTime_New(
					(long)(stv->ko->ob_type)));
			vinfo_setitem(po, vk, iOB_TYPE, vtype);
		}
		/* temporarily store vimpl in vk->array */
		vinfo_setitem(po, vk, iCOMPACT_IMPL, vimpl);
		l = psyco_atcompiletime(po, vimpl);
		psyco_assert(l == -1);   /* must be promoting here */
		return NULL;
	}
	else {
		/* case 2: resuming after promotion */
		psyco_assert(is_compiletime(vimpl->source));
		/* remove vimpl after promotion */
		l = CompileTime_Get(vimpl->source)->value;
		vinfo_setitem(po, vk, iCOMPACT_IMPL, NULL);
		if (is_virtualtime(vk->source)) {
			/* VirtualTime -> CompileTime */
			/* XXX fix this if virtual compactobjects
			   are introduced! */
			stv = ((struct source_tmp_virtual_s*)
					VirtualTime_Get(vk->source));
			vk->source = CompileTime_New((long) stv->ko);
		}
		return (compact_impl_t*) l;
	}
}

static vinfo_t* pcompact_getattro(PsycoObject* po, vinfo_t* vk, vinfo_t* vattr)
{
	PyTypeObject* tp;
	PyObject* descr = NULL;
	descrgetfunc f = NULL;
	compact_impl_t* impl;
	vinfo_t* vresult = NULL;
	PyObject* name;

	/* don't try to optimize non-constant attribute names
	   (see explanation in PsycoObject_GenericGetAttr()) */
	if (!is_compiletime(vattr->source)) {
		return psyco_generic_call(po, PyCompact_Type.tp_getattro,
					  CfReturnRef|CfPyErrIfNull,
					  "vv", vk, vattr);
	}

	/* we need the type of 'obj' at compile-time */
	tp = (PyTypeObject*) Psyco_NeedType(po, vk);
	if (tp == NULL)
		return NULL;

	if (tp->tp_dict == NULL) {
		if (PyType_Ready(tp) < 0) {
			psyco_virtualize_exception(po);
			return NULL;
		}
	}

	/* use interned strings only */
	name = (PyObject*) CompileTime_Get(vattr->source)->value;
	Py_INCREF(name);
	K_INTERN(name);

	/* XXX this is broken in the same way as PsycoObject_GenericGetAttr() */
	descr = _PyType_Lookup(tp, name);
	if (descr != NULL) {
		Py_INCREF(descr);
		if (PyType_HasFeature(descr->ob_type, Py_TPFLAGS_HAVE_CLASS)) {
			f = descr->ob_type->tp_descr_get;
			if (f != NULL && PyDescr_IsData(descr)) {
				vresult = Psyco_META3(po, f,
						      CfReturnRef|CfPyErrIfNull,
						      "lvl", descr, vk, tp);
				goto done;
			}
		}
	}

	/* read and temporarily promote the k_impl field of the object */
	impl = pcompact_getimpl(po, vk);
	if (impl == NULL)
		goto done;

	while (impl->attrname != NULL) {
		if (impl->attrname == name) {
			/* read the attribute data from the object and build a
			   copy of the attribute's vinfo to reflect the position
			   of the loaded data in the processor registers */
			vinfo_t* vdata = NULL;
			vresult = psy_k_load_vinfo(po, impl->vattr, vk, &vdata);
			vinfo_xdecref(vdata, po);
			goto done;
		}
		impl = impl->parent;
	}

	/* The end of PyObject_GenericGetAttr() */
	if (f != NULL) {
		vresult = Psyco_META3(po, f, CfReturnRef|CfPyErrIfNull,
				      "lvl", descr, vk, tp);
		goto done;
	}

	if (descr != NULL) {
		source_known_t* sk = sk_new((long) descr, SkFlagPyObj);
		descr = NULL;
		vresult = vinfo_new(CompileTime_NewSk(sk));
		goto done;
	}

	PycException_SetFormat(po, PyExc_AttributeError,
			       "'%.50s' object has no attribute '%.400s'",
			       tp->tp_name, PyString_AS_STRING(name));
 done:
	Py_XDECREF(descr);
	Py_DECREF(name);
	return vresult;
}


 /***************************************************************/
  /*** Meta-implementation of compact_setattro                 ***/

static void psy_k_mark_references(vinfo_t* v, bool mark)
{
	long pyobj_mask;
	switch (gettime(v->source)) {
		
	case VirtualTime:
		pyobj_mask = VirtualTime_Get(v->source)->pyobject_mask;
		break;

	case RunTime:
		if (mark)
			v->source = add_rtref(v->source);
		/* fall through */
	default:
		pyobj_mask = 0;
	}

	if (v->array != NullArray) {
		int i = v->array->count;
		while(--i >= 0) {
			vinfo_t* a = v->array->items[i];
			if (a != NULL)
				psy_k_mark_references(a, pyobj_mask & 1);
			pyobj_mask >>= 1;
		}
	}
}

static bool psy_k_store_vinfo(PsycoObject* po, vinfo_t* source_vi,
			      vinfo_t* attr_vi, vinfo_t* vk, vinfo_t** pvdata)
{
	/* generate code that writes 'source_vi' into the raw 'vdata'
	   using the format described by 'attr_vi' */
	int sindex;
	bool result;
	extra_assert(gettime(source_vi->source) == gettime(attr_vi->source));

	if (attr_vi->array != NullArray) {
		int i = attr_vi->array->count;
		while (--i >= 0) {
			if (attr_vi->array->items[i] == NULL)
				continue;
			extra_assert(source_vi->array->count > i);
			result = psy_k_store_vinfo(po,
						   source_vi->array->items[i],
						   attr_vi->array->items[i],
						   vk, pvdata);
			if (!result)
				return false;
		}
	}

	if (!is_runtime(attr_vi->source))
		return true;
	PSY_READ_K_DATA(*pvdata, return false);
	sindex = getstack(attr_vi->source);
	if (has_rtref(attr_vi->source)) {
		result = psyco_put_nth_field(po, *pvdata,
				KDATA_AS_PYOBJ, sindex / sizeof(PyObject*),
				source_vi);
	}
	else {
		result = psyco_put_nth_field(po, *pvdata,
				KDATA_AS_LONG, sindex / sizeof(long),
				source_vi);
	}
	return result;
}

static bool psy_k_decref_objects(PsycoObject* po, vinfo_t* attr_vi,
	 			 vinfo_t* vk, vinfo_t** pvdata)
{
	if (has_rtref(attr_vi->source)) {
		vinfo_t* v;
		int sindex = getstack(attr_vi->source);
		PSY_READ_K_DATA(*pvdata, return false);
		v = psyco_get_nth_field(po, *pvdata, KDATA_AS_PYOBJ_NOREF,
					sindex / sizeof(PyObject*));
		if (v == NULL)
			return false;
		v->source = add_rtref(v->source);  /* 'v' stole the reference
						      from the object */
		vinfo_decref(v, po);
	}
	if (attr_vi->array != NullArray) {
		int i = attr_vi->array->count;
		while (--i >= 0) {
			if (attr_vi->array->items[i] != NULL &&
			    !psy_k_decref_objects(po, attr_vi->array->items[i],
						  vk, pvdata))
				return false;
		}
	}
	return true;
}

static bool pcompact_setattro(PsycoObject* po, vinfo_t* vk, PyObject* attr,
			      vinfo_t* source_vi)
{
	PyTypeObject* tp;
	PyObject* descr;
	descrsetfunc f;
	vinfo_t* vimpl;
	compact_impl_t* impl;
	compact_impl_t* k_impl;
	vinfo_t* vcopy;
	condition_code_t cc;
	vinfo_array_t a;
	vinfo_t* vdata = NULL;
	vinfo_t* vndata;
	vinfo_t* v1;
	vinfo_t* v2;
	bool ok;
	int smin, smax, s, s1, s2;

	/* we need the type of 'obj' at compile-time */
	tp = (PyTypeObject*) Psyco_NeedType(po, vk);
	if (tp == NULL)
		return false;

	if (tp->tp_dict == NULL) {
		if (PyType_Ready(tp) < 0) {
			psyco_virtualize_exception(po);
			return false;
		}
	}

	/* XXX this is broken in the same way as PsycoObject_GenericGetAttr() */
	descr = _PyType_Lookup(tp, attr);
	if (descr != NULL &&
	    PyType_HasFeature(descr->ob_type, Py_TPFLAGS_HAVE_CLASS)) {
		f = descr->ob_type->tp_descr_set;
		if (f != NULL && PyDescr_IsData(descr)) {
			Py_INCREF(descr);   /* XXX leaks */
			return Psyco_META3(po, f,
					   CfNoReturnValue|CfPyErrIfNonNull,
					   source_vi ? "lvv" : "lvl",
					   descr, vk, source_vi) != NULL;
		}
	}

	if (source_vi != NULL) {
		/* force mutable virtual-time objects out of virtual-time,
		   and limit the virtual depth a bit */
		a.count = 1;
		a.items[0] = source_vi;
		if (!psyco_forking(po, &a))
			return false;
		clear_tmp_marks(&a);
		psyco_simplify_array(&a, po);
	}

	/* read and temporarily promote the k_impl field of the object */
	k_impl = pcompact_getimpl(po, vk);
	if (k_impl == NULL)
		return false;
	
	for (impl = k_impl; impl->attrname != NULL; impl = impl->parent) {
		if (impl->attrname != attr)
			continue;
		if (!psy_k_decref_objects(po, impl->vattr, vk, &vdata))
			goto error;
		if (k_match_vinfo(source_vi, impl->vattr)) {
			/* the attr already has the correct format */
			if (!psy_k_store_vinfo(po, source_vi, impl->vattr,
					       vk, &vdata))
				goto error;
			vinfo_xdecref(vdata, po);
			return true;
		}
		/* a format change is needed: first delete the
		 * existing attribute.
		 * XXX same restrictions as in compact_setattro().
		 * XXX it's already far too scary.
		 */
		smin = impl->datasize;
		smax = 0;
		k_attribute_range(impl->vattr, &smin, &smax);
		if (smax < smin)
			smax = smin;

		/* data between smin and smax is removed */
		if (smin < smax && smax < k_impl->datasize) {
			PSY_READ_K_DATA(vdata, return false);
			extra_assert((smin % sizeof(long)) == 0);
			extra_assert((smax % sizeof(long)) == 0);
			extra_assert((k_impl->datasize % sizeof(long)) == 0);
			if (k_impl->datasize-smax <= 5*sizeof(long)) {
				s1 = smax/sizeof(long);
				s2 = k_impl->datasize/sizeof(long);
				for (s=s1; s<s2; s++) {
					v1 = psyco_get_nth_field(po, vdata,
						KDATA_AS_LONG, s);
					if (v1 == NULL)
						goto error;
					psyco_put_nth_field(po, vdata,
						KDATA_AS_LONG,
						s + (smin-smax)/sizeof(long),
						v1);
					vinfo_decref(v1, po);
				}
			}
			else {
				/* don't unroll too much */
				v1 = integer_add_i(po, vdata, smin, false);
				if (v1 == NULL)
					goto error;
				v2 = integer_add_i(po, vdata, smax, false);
				if (v2 == NULL) {
					vinfo_decref(v1, po);
					goto error;
				}
				ok = psyco_generic_call(po, memmove,
							CfNoReturnValue,
							"vvl", v1, v2,
							k_impl->datasize-smax)
					!= NULL;
				vinfo_decref(v2, po);
				vinfo_decref(v1, po);
				if (!ok)
					goto error;
			}
		}

		/* make the new 'impl' by starting from impl->parent
		   and accounting for all following attrs excluding
		   'impl', shifted as per memmove() */
		impl = k_duplicate_impl(impl->parent, impl,
					k_impl, smin - smax);

		if (source_vi != NULL)
			goto store_data; /* now, re-create the attr
					    under its new format */

		goto update_k_impl; /* if attribute deletion: done */
	}

	if (source_vi == NULL) {
		/* deleting a non-existing attribute */
		return psyco_generic_call(po, PyObject_GenericSetAttr,
					  CfNoReturnValue|CfPyErrIfNonNull,
					  "vll", vk, attr, (long) NULL) != NULL;
	}

	/* setting a new attribute */
	impl = k_impl;
	
	/* XXX Psyco's error handling on top of Python's error handling code
	       is the best recipe for scary sources */

 store_data:
	vcopy = vinfo_copy_no_share(source_vi);
	psy_k_mark_references(vcopy, true);
	impl = k_extend_impl(impl, attr, vcopy);
	vinfo_decref(vcopy, NULL);

	/* generate the operations of PyCompact_Extend() in-line: */
	if (impl->datasize <= K_ROUNDUP(k_impl->datasize)) {
		/* already enough space */
	}
	else {
		PSY_READ_K_DATA(vdata, return false);
		
		/* call PyMem_Realloc() on k->k_data */
		vndata = psyco_generic_call(po, PyMem_Realloc, CfReturnNormal,
					    "vl", vdata,
					    K_ROUNDUP(impl->datasize));
		if (vndata == NULL)
			goto error;
		vinfo_decref(vdata, po);
		vdata = vndata;
		/* did PyMem_Realloc() return NULL? */
		cc = integer_non_null(po, vdata);
		if (cc == CC_ERROR)
			goto error;
		if (!runtime_condition_t(po, cc)) {
			/* yes -> raise a MemoryError */
			PycException_SetVInfo(po, PyExc_MemoryError,
					      psyco_vi_None());
			goto error;
		}
		/* store the result of PyMem_Realloc() back into
		   ko->k_data */
		if (!psyco_put_field(po, vk, COMPACT_data, vdata))
			goto error;
	}
	/* store 'v' into the newly allocated data */
	if (!psy_k_store_vinfo(po, source_vi, impl->vattr, vk, &vdata))
		goto error;

	/* update ko->k_impl with the extended compact_impl_t */
 update_k_impl:
	vinfo_xdecref(vdata, po);
	vimpl = vinfo_new(CompileTime_New((long) impl));
	ok = psyco_put_field(po, vk, COMPACT_impl, vimpl);
	vinfo_decref(vimpl, po);
	return ok;

 error:
	vinfo_xdecref(vdata, po);
	return false;
}


 /***************************************************************/
  /*** More meta-implementations                               ***/

static vinfo_t* pcompact_new(PsycoObject* po, PyTypeObject* type,
			     vinfo_t* vargs, vinfo_t* vkwds)
{
	/* first delegate to object_new() */
	bool ok;
	vinfo_t* vimpl;
	vinfo_t* vk = psyco_pobject_new(po, type, vargs, vkwds);
	if (vk != NULL) {
		extra_assert(Psyco_KnownType(vk) == type);
		vimpl = vinfo_new(CompileTime_New((long) PyCompact_EmptyImpl));
		ok = psyco_put_field(po, vk, COMPACT_impl, vimpl);
		vinfo_decref(vimpl, po);
		if (!ok) {
			vinfo_decref(vk, po);
			return NULL;
		}
	}
	return vk;
}


 /***************************************************************/
  /***   Virtual-time compact objects                          ***/

/* A compact object allocated in the heap contains raw data and a pointer
   to a compact_impl_t structure that may describe that some of this raw
   data represents further virtual-time objects.  This is implemented in
   compactobject.c and optimized in pcompact_getattro/pcompact_setattro
   above the present point.

   This section implements a further optimization: compact objects that
   are not yet allocated in the heap at all.  This only applies to
   newly created compact objects.

   XXX NOT DONE YET
*/

#if 0
static source_virtual_t psyco_computed_compact;

static
vinfo_t* PsycoCompactObject_New(PyTypeObject* tp)
{
	vinfo_t* result = vinfo_new(VirtualTime_New(&psyco_computed_compact));
	result->array = array_new(COMPACT_TOTAL);
	result->array->items[iOB_TYPE] =
		vinfo_new(CompileTime_New((long) tp));
	result->array->items[iCOMPACT_IMPL] =
		vinfo_new(CompileTime_New((long) &k_empty_impl));
	result->array->items[iCOMPACT_DATA] = psyco_vi_Zero();
        
	vinfo_incref(self);
	result->array->items[iMETHOD_IM_SELF] = self;
        
        Py_INCREF(cls);
	result->array->items[iMETHOD_IM_CLASS] =
		vinfo_new(CompileTime_NewSk(sk_new((long) cls, SkFlagPyObj)));
        
	return result;
}
#endif

 /***************************************************************/

INITIALIZATIONFN
void psy_compactobject_init(void)
{
	Psyco_DefineMeta(PyCompact_Type.tp_getattro, pcompact_getattro);
	Psyco_DefineMeta(PyCompact_Type.tp_setattro, pcompact_setattro);
	Psyco_DefineMeta(PyCompact_Type.tp_new,      pcompact_new);
}
