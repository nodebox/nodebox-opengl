#include "compactobject.h"
#include "../blockalloc.h"
#include "../dispatcher.h"
#include "../Python/pycompiler.h"
#include "pintobject.h"


#define DEBUG_K_IMPL   0


BLOCKALLOC_STATIC(kimpl, compact_impl_t, 4096)


static compact_impl_t k_empty_impl = {
	NULL,          /* attrname */
	NULL,          /* vattr */
	0,             /* datasize */
	NULL,          /* extensions */
	NULL,          /* next */
	NULL,          /* parent */
};

/*****************************************************************/

#if DEBUG_K_IMPL

static void debug_k_impl(compact_impl_t* p)
{
	int smin, smax;
	compact_impl_t *q, *lim;
	fprintf(stderr, "\t$ ");
	lim = &k_empty_impl;
	while (p != lim) {
		for (q=p; q->parent != lim; q = q->parent)
			;
		fprintf(stderr, "  %s", PyString_AsString(q->attrname));
		smin = p->datasize;
		smax = 0;
		k_attribute_range(q->vattr, &smin, &smax);
		if (smin < smax)
			fprintf(stderr, "(%d-%d)", smin, smax);
		else
			fprintf(stderr, "(void)");
		lim = q;
	}
	fprintf(stderr, ".\n");
}

#else  /* !DEBUG_K_IMPL */
# define debug_k_impl(p)   /* nothing */
#endif

/*****************************************************************/

/* static int */
/* compact_init(PyObject *self, PyObject *args, PyObject *kwds) */
/* { */
/* 	return 0; */
/* } */

static newfunc object_new;

static PyObject *
compact_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
	PyObject* ko = object_new(type, args, kwds);
	if (ko != NULL) {
		((PyCompactObject*) ko)->k_impl = &k_empty_impl;
	}
	return ko;
}

#if 0
DEFINEFN
PyObject* PyCompact_New(void)
{
	PyCompactObject* o = PyObject_GC_New(PyCompactObject, &PyCompact_Type);
	if (o != NULL) {
		o->k_impl = &k_empty_impl;
		o->k_data = NULL;
		PyObject_GC_Track(o);
	}
	return (PyObject*) o;
}
#endif

static bool k_same_vinfo(vinfo_t* a, vinfo_t* b)
{
	if (a->source != b->source) {
		if (is_compiletime(a->source) && is_compiletime(b->source))
			return (CompileTime_Get(a->source)->value ==
				CompileTime_Get(b->source)->value);
		else
			return false;
	}
	if (a->array != b->array) {
		int i = a->array->count;
		if (i != b->array->count)
			return false;
		while (--i >= 0) {
			if (a->array->items[i] == b->array->items[i])
				continue;
			if (a->array->items[i] == NULL ||
			    b->array->items[i] == NULL)
				return false;
			if (!k_same_vinfo(a->array->items[i],
					  b->array->items[i]))
				return false;
		}
	}
	return true;
}

static int k_fix_run_time_vars(vinfo_t* a, int datasize)
{
	if (is_runtime(a->source)) {
		bool ref = has_rtref(a->source);
		int sindex = datasize;
		datasize += sizeof(long);
		extra_assert(sizeof(long) == sizeof(PyObject*));
		a->source = RunTime_NewStack(sindex, ref, false);
	}
	if (a->array != NullArray) {
		int i, n = a->array->count;
		for (i=0; i<n; i++) {
			if (a->array->items[i] != NULL)
				datasize = k_fix_run_time_vars(
						a->array->items[i], datasize);
		}
	}
	return datasize;
}

DEFINEFN
compact_impl_t* k_extend_impl(compact_impl_t* oldimpl, PyObject* attr,
			      vinfo_t* v)
{
	int datasize;
	compact_impl_t* p;
	extra_assert(PyString_CheckExact(attr) && PyString_CHECK_INTERNED(attr));

	/* enumerate the run-time entries */
	datasize = k_fix_run_time_vars(v, oldimpl->datasize);

	/* look for a matching existing extension of oldimpl */
	for (p = oldimpl->extensions; p != NULL; p = p->next) {
		if (p->attrname == attr && p->datasize == datasize &&
		    k_same_vinfo(v, p->vattr))
			return p;
	}

	/* build a new impl */
	p = psyco_llalloc_kimpl();
	p->attrname = attr;
	Py_INCREF(attr);
	p->vattr = v;
	vinfo_incref(v);
	p->datasize = datasize;
	p->extensions = NULL;
	p->next = oldimpl->extensions;
	oldimpl->extensions = p;
	p->parent = oldimpl;
        debug_k_impl(p);
        return p;
}

#if PSYCO_DEBUG
static int k_check_extension(compact_impl_t* impl1, compact_impl_t* impl2)
{
	while (impl1 != impl2) {
		impl1 = impl1->parent;
		if (impl1 == NULL)
			return false;
	}
	return true;
}
#endif

static int k_extend(PyCompactObject* ko, compact_impl_t* nimpl)
{
	char* ndata;
	extra_assert(k_check_extension(nimpl, ko->k_impl));
	if (nimpl->datasize > K_ROUNDUP(ko->k_impl->datasize)) {
		ndata = ko->k_data;
		ndata = (char*) PyMem_Realloc(ndata,
					      K_ROUNDUP(nimpl->datasize));
		if (ndata == NULL) {
			PyErr_NoMemory();
			return -1;
		}
		ko->k_data = ndata;
	}
	ko->k_impl = nimpl;
	return 0;
}

DEFINEFN
vinfo_t* vinfo_copy_no_share(vinfo_t* vi)
{
	vinfo_t* result = vinfo_new_skref(vi->source);
	if (vi->array != NullArray) {
		int i = vi->array->count;
		vinfo_array_grow(result, i);
		while (--i >= 0) {
			if (vi->array->items[i] != NULL)
				result->array->items[i] =
				    vinfo_copy_no_share(vi->array->items[i]);
		}
	}
	return result;
}


/*****************************************************************/

/* decref all PyObjects found in the CompactObject */
static void k_decref_objects(vinfo_t* a, char* data)
{
	if (has_rtref(a->source)) {
		int sindex = getstack(a->source);
		PyObject* o = *(PyObject**)(data+sindex);
		Py_DECREF(o);
	}
	if (a->array != NullArray) {
		int i = a->array->count;
		while (--i >= 0) {
			if (a->array->items[i] != NULL)
				k_decref_objects(a->array->items[i], data);
		}
	}
}

static void compact_dealloc(PyCompactObject* ko)
{
	compact_impl_t* impl = ko->k_impl;
	while (impl->vattr != NULL) {
		k_decref_objects(impl->vattr, ko->k_data);
		impl = impl->parent;
	}
	PyMem_Free(ko->k_data);
	ko->ob_type->tp_free((PyObject*) ko);
}

static int k_traverse_objects(vinfo_t* a, char* data,
			      visitproc visit, void* arg)
{
	int err;
	if (has_rtref(a->source)) {  /* run-time && with reference */
		int sindex = getstack(a->source);
		PyObject* o = *(PyObject**)(data+sindex);
		err = visit(o, arg);
		if (err)
			return err;
	}
	if (a->array != NullArray) {
		int i = a->array->count;
		while (--i >= 0) {
			if (a->array->items[i] != NULL) {
				err = k_traverse_objects(a->array->items[i],
							 data, visit, arg);
				if (err)
					return err;
			}
		}
	}
	return 0;
}

static int compact_traverse(PyCompactObject* ko, visitproc visit, void* arg)
{
	int err;
	compact_impl_t* impl = ko->k_impl;
	while (impl->vattr != NULL) {
		err = k_traverse_objects(impl->vattr, ko->k_data, visit, arg);
		if (err)
			return err;
		impl = impl->parent;
	}
	return 0;
}

static int compact_clear(PyCompactObject* ko)
{
	compact_impl_t* impl = ko->k_impl;
	char*           data = ko->k_data;
	ko->k_impl = &k_empty_impl;
	ko->k_data = NULL;
	while (impl->vattr != NULL) {
		k_decref_objects(impl->vattr, data);
		impl = impl->parent;
	}
	PyMem_Free(data);
	return 0;
}


/*****************************************************************/

static PyObject* compact_getattro(PyCompactObject* ko, PyObject* attr)
{
	PyTypeObject* tp = ko->ob_type;
	PyObject* descr;
	descrgetfunc f = NULL;
	compact_impl_t* impl = ko->k_impl;
	PyObject* o;

	if (tp->tp_dict == NULL) {
		if (PyType_Ready(tp) < 0)
			return NULL;
	}

	Py_INCREF(attr);
	K_INTERN(attr);

	/* Special code for data descriptors first, as in
					PyObject_GenericGetAttr() */
	descr = _PyType_Lookup(tp, attr);
	if (descr != NULL) {
		Py_INCREF(descr);
		if (PyType_HasFeature(descr->ob_type, Py_TPFLAGS_HAVE_CLASS)) {
			f = descr->ob_type->tp_descr_get;
			if (f != NULL && PyDescr_IsData(descr)) {
				o = f(descr, (PyObject*) ko, (PyObject*) tp);
				Py_DECREF(descr);
				goto done;
			}
		}
	}

	/* Read data out of the compact memory buffer */
	while (impl->attrname != NULL) {
		if (impl->attrname == attr) {
			o = direct_xobj_vinfo(impl->vattr, ko->k_data);
			if (o != NULL || PyErr_Occurred()) {
				Py_XDECREF(descr);
				goto done;
			}
		}
		impl = impl->parent;
	}

	/* The end of PyObject_GenericGetAttr() */
	if (f != NULL) {
		o = f(descr, (PyObject*) ko, (PyObject*) tp);
		Py_DECREF(descr);
		goto done;
	}

	if (descr != NULL) {
		o = descr;
		/* descr was already increfed above */
		goto done;
	}

	o = NULL;
	PyErr_Format(PyExc_AttributeError,
		     "'%.50s' object has no attribute '%.400s'",
		     tp->tp_name, PyString_AS_STRING(attr));
 done:
	Py_DECREF(attr);
	return o;
}

DEFINEFN
bool k_match_vinfo(vinfo_t* vnew, vinfo_t* vexisting)
{
	if (vnew == NULL)
		return vexisting == NULL;
	if (vexisting == NULL)
		return false;
	switch (gettime(vnew->source)) {

	case RunTime:
		if (!is_runtime(vexisting->source))
			return false;
		break;

	case CompileTime:
		if (!is_compiletime(vexisting->source))
			return false;
		return CompileTime_Get(vnew->source)->value ==
			CompileTime_Get(vexisting->source)->value;

	case VirtualTime:
		if (vexisting->source != vnew->source)
			return false;
		break;
	}
	if (vnew->array != vexisting->array) {
		int i, n = vexisting->array->count;
		if (n != vnew->array->count)
			return false;
		for (i=0; i<n; i++) {
			if (!k_match_vinfo(vnew->array->items[i],
				      vexisting->array->items[i]))
				return false;
		}
	}
	return true;
}

static char* k_store_vinfo(vinfo_t* v, char* target, char* source)
{
	if (is_runtime(v->source)) {
		int sindex = getstack(v->source);
		if (has_rtref(v->source)) {
			PyObject* o = *(PyObject**) source;
			source += sizeof(PyObject*);
			*(PyObject**)(target+sindex) = o;
			Py_INCREF(o);
		}
		else {
			long l = *(long*) source;
			source += sizeof(long);
			*(long*)(target+sindex) = l;
		}
	}
	if (v->array != NullArray) {
		int i, n = v->array->count;
		for (i=0; i<n; i++) {
			if (v->array->items[i] != NULL)
				source = k_store_vinfo(v->array->items[i],
						       target, source);
		}
	}
	return source;
}

DEFINEFN
void k_attribute_range(vinfo_t* v, int* smin, int* smax)
{
	/* XXX Assumes that the data for an attr is stored consecutively */
	if (is_runtime(v->source)) {
		int sindex = getstack(v->source);
		if (*smin > sindex)
			*smin = sindex;
		sindex += sizeof(PyObject*);
		extra_assert(sizeof(PyObject*) == sizeof(long));
		if (*smax < sindex)
			*smax = sindex;
	}
	if (v->array != NullArray) {
		int i = v->array->count;
		while (--i >= 0) {
			if (v->array->items[i] != NULL)
				k_attribute_range(v->array->items[i],
						  smin, smax);
		}
	}
}

static void k_shift_rt_pos(vinfo_t* v, int delta)
{
	if (is_runtime(v->source)) {
		v->source += delta;
	}
	if (v->array != NullArray) {
		int i = v->array->count;
		while (--i >= 0) {
			if (v->array->items[i] != NULL)
				k_shift_rt_pos(v->array->items[i], delta);
		}
	}
}

DEFINEFN
compact_impl_t* k_duplicate_impl(compact_impl_t* base,
				 compact_impl_t* first_excluded,
				 compact_impl_t* last,
				 int shift_delta)
{
	vinfo_t* v;
	if (first_excluded == last)
		return base;
	base = k_duplicate_impl(base, first_excluded, last->parent,
				shift_delta);
	v = vinfo_copy_no_share(last->vattr);
	k_shift_rt_pos(v, shift_delta);
	return k_extend_impl(base, last->attrname, v);
}

static
int compact_set(PyCompactObject* ko, PyObject* attr, PyObject* value,
		PyObject* pyerr_notfound)
{
	int err, smin, smax;
	long immed_value;
	vinfo_t* source_vi;
	char* source_data;
	compact_impl_t* impl;
	compact_impl_t* p;

	/* recognize a few obvious object types and optimize accordingly
	   Note that this is not related to Psyco's ability to store
	   attributes with arbitrary flexibility, which is implemented in
	   pcompactobject.c. */
	if (value == NULL) {
		source_vi = NULL;
		source_data = NULL;
	}
	else if (PyInt_CheckExact(value)) {
		immed_value = PyInt_AS_LONG(value);
		source_vi = PsycoInt_FROM_LONG(vinfo_new(SOURCE_DUMMY));
		source_data = (char*) &immed_value;
	}
	else if (value == Py_None) {
		source_vi = psyco_vi_None();
		source_data = NULL;
	}
	else {
		source_vi = vinfo_new(SOURCE_DUMMY_WITH_REF);
		source_data = (char*) &value;
	}
	impl = ko->k_impl;
	while (impl->attrname != NULL) {
		if (impl->attrname == attr) {
			k_decref_objects(impl->vattr, ko->k_data);
			
			if (k_match_vinfo(source_vi, impl->vattr)) {
				/* the attr already has the correct format */
				k_store_vinfo(impl->vattr, ko->k_data,
					      source_data);
				err = 0;
				goto finally;
			}

			/* a format change is needed: first delete the
			 * existing attribute.
			 * XXX Not too efficient right now.
			 * XXX Also assumes that attribute order matches
			 * XXX data storage order.
			 */
			smin = ko->k_impl->datasize;
			smax = 0;
			k_attribute_range(impl->vattr, &smin, &smax);
			if (smax < smin)
				smax = smin;
			
			/* data between smin and smax is removed */
			memmove(ko->k_data + smin,
                                ko->k_data + smax,
                                ko->k_impl->datasize - smax);

			/* make the new 'impl' by starting from impl->parent
			   and accounting for all following attrs excluding
			   'impl', shifted as per memmove() */
			ko->k_impl = k_duplicate_impl(impl->parent, impl,
						      ko->k_impl, smin - smax);

			if (source_vi != NULL)
				goto store_data; /* now, re-create the attr
						    under its new format */
			err = 0;
			goto finally;   /* if attribute deletion: done */
		}
		impl = impl->parent;
	}

	if (source_vi == NULL) {
		/* deleting a non-existing attribute */
		PyErr_SetObject(pyerr_notfound, attr);
		return -1;
	}

	/* setting a new attribute */
 store_data:
	p = k_extend_impl(ko->k_impl, attr, source_vi);
	err = k_extend(ko, p);
	if (err == 0) {
		k_store_vinfo(p->vattr, ko->k_data, source_data);
	}

 finally:
	vinfo_xdecref(source_vi, NULL);
	return err;
}

static
int compact_setattro(PyCompactObject* ko, PyObject* attr, PyObject* value)
{
	PyTypeObject* tp = ko->ob_type;
	PyObject* descr;
	descrsetfunc f;

        /* NB. this assumes that 'attr' is an already-interned string.
           PyObject_SetAttr() should have interned it. */

	/* Special code for data descriptors first, as in
					PyObject_GenericSetAttr() */
	if (tp->tp_dict == NULL) {
		if (PyType_Ready(tp) < 0)
			return -1;
	}
	descr = _PyType_Lookup(tp, attr);
	if (descr != NULL &&
	    PyType_HasFeature(descr->ob_type, Py_TPFLAGS_HAVE_CLASS)) {
		f = descr->ob_type->tp_descr_set;
		if (f != NULL && PyDescr_IsData(descr))
			return f(descr, (PyObject*) ko, value);
	}

	return compact_set(ko, attr, value, PyExc_AttributeError);
}

static PyObject* k_interned_key(PyObject* key)
{
	if (key->ob_type != &PyString_Type) {
		if (!PyString_Check(key)) {
			PyErr_SetString(PyExc_TypeError,
					"keys in compact objects "
					"must be strings");
			return NULL;
		}
		key = PyString_FromStringAndSize(PyString_AS_STRING(key),
						 PyString_GET_SIZE(key));
		if (key == NULL)
			return NULL;
	}
	else {
		Py_INCREF(key);
	}
	K_INTERN(key);
	return key;
}

#if 0
DEFINEFN
PyObject* PyCompact_GetSlot(PyObject* ko, PyObject* key)
{
	compact_impl_t* impl;
	PyObject* o;

	if (!PyCompact_Check(ko)) {
		PyErr_BadInternalCall();
		return NULL;
	}

	key = k_interned_key(key);
	if (key == NULL)
		return NULL;
	
	impl = ((PyCompactObject*) ko)->k_impl;
	while (impl->attrname != NULL) {
		if (impl->attrname == key) {
			o = direct_xobj_vinfo(impl->vattr,
					      ((PyCompactObject*) ko)->k_data);
			if (o != NULL || PyErr_Occurred())
				goto finally;
		}
		impl = impl->parent;
	}
	PyErr_SetObject(PyExc_KeyError, key);
	o = NULL;
 finally:
	Py_DECREF(key);
	return o;
}

DEFINEFN
PyObject* PyCompact_SetSlot(PyObject* ko, PyObject* key, PyObject* value)
{
	int err;

	if (!PyCompact_Check(ko)) {
		PyErr_BadInternalCall();
		return NULL;
	}

	key = k_interned_key(key);
	if (key == NULL)
		return NULL;

	err = compact_set((PyCompactObject*) ko, key, value,
			  PyExc_KeyError);
	Py_DECREF(key);
	return err;
}
#endif

static PyObject* compact_getslot(PyCompactObject* ko, PyObject* key)
{
	compact_impl_t* impl = ko->k_impl;
	PyObject* o;

	key = k_interned_key(key);
	if (key == NULL)
		return NULL;

	while (impl->attrname != NULL) {
		if (impl->attrname == key) {
			o = direct_xobj_vinfo(impl->vattr, ko->k_data);
			if (o != NULL || PyErr_Occurred())
				goto finally;
		}
		impl = impl->parent;
	}
	PyErr_SetObject(PyExc_KeyError, key);
	o = NULL;
 finally:
	Py_DECREF(key);
	return o;
}

static PyObject* compact_setslot(PyCompactObject* ko, PyObject* args)
{
	PyObject* key;
	PyObject* value;
	int err;

	if (!PyArg_ParseTuple(args, "OO", &key, &value))
		return NULL;

	key = k_interned_key(key);
	if (key == NULL)
		return NULL;

	err = compact_set(ko, key, value, PyExc_KeyError);
	Py_DECREF(key);
	if (err < 0)
		return NULL;
	Py_INCREF(Py_None);
	return Py_None;
}

static PyObject* compact_delslot(PyCompactObject* ko, PyObject* key)
{
	int err;

	key = k_interned_key(key);
	if (key == NULL)
		return NULL;

	err = compact_set(ko, key, NULL, PyExc_KeyError);
	Py_DECREF(key);
	if (err < 0)
		return NULL;
	Py_INCREF(Py_None);
	return Py_None;
}

static PyObject* compact_getmembers(PyCompactObject* ko, void* context)
{
	compact_impl_t* impl = ko->k_impl;
	PyObject* result = PyList_New(0);
	if (result == NULL)
		return NULL;
	while (impl->attrname != NULL) {
		if (PyList_Append(result, impl->attrname) < 0) {
			Py_DECREF(result);
			return NULL;
		}
		impl = impl->parent;
	}
	if (PyList_Reverse(result) < 0) {
		Py_DECREF(result);
		return NULL;
	}
	return result;
}

static PyObject* compact_getdict(PyObject* ko, void* context)
{
	PyObject* t = need_cpsyco_obj("compactdictproxy");
	if (t == NULL)
		return NULL;
	return PyObject_CallFunction(t, "O", ko);
}

static int compact_setdict(PyObject* ko, PyObject* value, void* context)
{
	PyObject* nval;
	PyObject* d;
	PyObject* tmp;

	if (value == NULL) {
		PyErr_SetString(PyExc_AttributeError,
				"__dict__ attribute cannot be deleted");
		return -1;
	}
	if (PyDict_Check(value)) {
		nval = value;
		Py_INCREF(nval);
	}
	else {
		/* Force a complete copy of 'value' for the assignment
		   x.__dict__ = x.__dict__.  Note that we could do better
		   and just copy the memory buffer if we detect that
		   'value' is the dict proxy of another compact object. */
		if (!PyMapping_Check(value)) {
			PyErr_SetString(PyExc_TypeError,
					"__dict__ attribute must be set "
					"to a mapping");
			return -1;
		}
		nval = PyDict_New();
		if (nval == NULL)
			return -1;
		if (PyDict_Merge(nval, value, 1) < 0)
			goto error;
	}
	d = compact_getdict(ko, context);
	if (d == NULL)
		goto error;
	tmp = PyObject_CallMethod(d, "clear", "");
	if (tmp == NULL)
		goto error;
	Py_DECREF(tmp);
	tmp = PyObject_CallMethod(d, "update", "O", nval);
	if (tmp == NULL)
		goto error;
	Py_DECREF(tmp);
	Py_DECREF(nval);
	return 0;

 error:
	Py_DECREF(nval);
	return -1;
}


/*****************************************************************/
/*  The custom metaclass 'psyco.compacttype'.
 *  The only difference with the standard 'type' is that it
 *  forces some values:
 *     __slots__ == ()
 *     __bases__[-1] == psyco.compact
 */

staticforward PyTypeObject PyCompactType_Type;

static PyObject *
compacttype_new(PyTypeObject *metatype, PyObject *args, PyObject *kwds)
{
	int i, n;
	PyObject *name, *bases, *dict, *slots, *result, *nbases;
	static char *kwlist[] = {"name", "bases", "dict", 0};

	/* Check arguments: (name, bases, dict) */
	if (!PyArg_ParseTupleAndKeywords(args, kwds, "SO!O!:compacttype",
					 kwlist,
					 &name,
					 &PyTuple_Type, &bases,
					 &PyDict_Type, &dict))
		return NULL;

	slots = PyDict_GetItemString(dict, "__slots__");
	if (slots != NULL) {
		/* Specifying __slots__ on compacttypes is forbidden! */
		PyErr_SetString(PyExc_PsycoError, "psyco.compact classes "
				"cannot have an explicit __slots__");
		return NULL;
	}

	args = PyTuple_New(3);
	if (args == NULL)
		return NULL;
	PyTuple_SET_ITEM(args, 0, name); Py_INCREF(name);

	/* Append 'psyco.compact' to bases if necessary, i.e. if none of the
	   provided bases already has a metaclass of psyco.compacttype.
	   The goal is to ensure that all the instances of psyco.compacttype
	   are classes that inherit from psyco.compact, but only add
	   psyco.compact to the bases if absolutely necessary. */
	n = PyTuple_GET_SIZE(bases);
	for (i=0; i<n; i++) {
		if (PyObject_TypeCheck(PyTuple_GET_ITEM(bases, i),
				       &PyCompactType_Type))
			break;
	}
	if (i == n) {
		/* no suitable base found, must append 'psyco.compact' */
		nbases = PyTuple_New(n+1);
		if (nbases == NULL) {
			Py_DECREF(args);
			return NULL;
		}
		for (i=0; i<n; i++) {
			PyObject* o = PyTuple_GET_ITEM(bases, i);
			PyTuple_SET_ITEM(nbases, i, o);
			Py_INCREF(o);
		}
		PyTuple_SET_ITEM(nbases, n, (PyObject*) &PyCompact_Type);
		Py_INCREF(&PyCompact_Type);
	}
	else {
		nbases = bases;
		Py_INCREF(bases);
	}
	PyTuple_SET_ITEM(args, 1, nbases);

	/* Insert '__slots__=()' into a copy of 'dict' */
	dict = PyDict_Copy(dict);
	slots = PyTuple_New(0);
	if (dict == NULL || slots == NULL ||
	    PyDict_SetItemString(dict, "__slots__", slots) < 0) {
		Py_XDECREF(slots);
		Py_XDECREF(dict);
		Py_DECREF(args);
		return NULL;
	}
	PyTuple_SET_ITEM(args, 2, dict);
	Py_DECREF(slots);

	/* Call the base type's tp_new() to actually create the class */
	result = PyType_Type.tp_new(metatype, args, NULL);
	Py_DECREF(args);
	return result;
}

statichere PyTypeObject PyCompactType_Type = {
	PyObject_HEAD_INIT(NULL)
	0,                                      /*ob_size*/
	"psyco.compacttype",                    /*tp_name*/
	0,                                      /*tp_size*/
	0,                                      /*tp_itemsize*/
	/* methods */
	0,                                      /* tp_dealloc */
	0,                                      /* tp_print */
	0,                                      /* tp_getattr */
	0,                                      /* tp_setattr */
	0,                                      /* tp_compare */
	0,                                      /* tp_repr */
	0,                                      /* tp_as_number */
	0,                                      /* tp_as_sequence */
	0,                                      /* tp_as_mapping */
	0,                                      /* tp_hash */
	0,                                      /* tp_call */
	0,                                      /* tp_str */
	0,                                      /* tp_getattro */
	0,                                      /* tp_setattro */
	0,                                      /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT |
		Py_TPFLAGS_BASETYPE,		/* tp_flags */
	0,                                      /* tp_doc */
	0,                                      /* tp_traverse */
	0,                                      /* tp_clear */
	0,                                      /* tp_richcompare */
	0,                                      /* tp_weaklistoffset */
	0,                                      /* tp_iter */
	0,                                      /* tp_iternext */
	0,                                      /* tp_methods */
	0,                                      /* tp_members */
	0,                                      /* tp_getset */
	/*&PyType_Type set below*/ 0,           /* tp_base */
	0,                                      /* tp_dict */
	0,                                      /* tp_descr_get */
	0,                                      /* tp_descr_set */
	0,                                      /* tp_dictoffset */
	0,                                      /* tp_init */
	0,                                      /* tp_alloc */
	compacttype_new,                        /* tp_new */
	0,                                      /* tp_free */
};


/*****************************************************************/

DEFINEVAR compact_impl_t* PyCompact_EmptyImpl;

static PyMethodDef compact_methods[] = {
	{"__getslot__",	(PyCFunction)compact_getslot, METH_O, NULL},
	{"__setslot__",	(PyCFunction)compact_setslot, METH_VARARGS, NULL},
	{"__delslot__",	(PyCFunction)compact_delslot, METH_O, NULL},
	{NULL,		NULL}		/* sentinel */
};

static PyGetSetDef compact_getsets[] = {
	{"__members__", (getter)compact_getmembers, NULL, NULL},
	{"__dict__", compact_getdict, compact_setdict, NULL},
	{NULL}
};

DEFINEVAR PyTypeObject PyCompact_Type = {
	PyObject_HEAD_INIT(&PyCompactType_Type)
	0,                                      /*ob_size*/
	"psyco.compact",                        /*tp_name*/
	sizeof(PyCompactObject),                /*tp_size*/
	0,                                      /*tp_itemsize*/
	/* methods */
	(destructor)compact_dealloc,            /* tp_dealloc */
	0,                                      /* tp_print */
	0,                                      /* tp_getattr */
	0,                                      /* tp_setattr */
	0,                                      /* tp_compare */
	0,                                      /* tp_repr */
	0,                                      /* tp_as_number */
	0,                                      /* tp_as_sequence */
	0,                                      /* tp_as_mapping */
	0,                                      /* tp_hash */
	0,                                      /* tp_call */
	0,                                      /* tp_str */
	(getattrofunc)compact_getattro,         /* tp_getattro */
	(setattrofunc)compact_setattro,         /* tp_setattro */
	0,                                      /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC |
		Py_TPFLAGS_BASETYPE,		/* tp_flags */
	0,                                      /* tp_doc */
	(traverseproc)compact_traverse,         /* tp_traverse */
	(inquiry)compact_clear,                 /* tp_clear */
	0,                                      /* tp_richcompare */
	0,                                      /* tp_weaklistoffset */
	0,                                      /* tp_iter */
	0,                                      /* tp_iternext */
	compact_methods,                        /* tp_methods */
	0,                                      /* tp_members */
	compact_getsets,                        /* tp_getset */
	0,                                      /* tp_base */
	0,                                      /* tp_dict */
	0,                                      /* tp_descr_get */
	0,                                      /* tp_descr_set */
	0,                                      /* tp_dictoffset */
	0,                                      /* tp_init */
	0,                                      /* tp_alloc */
	compact_new,                            /* tp_new */
};

INITIALIZATIONFN
void psyco_compact_init(void)
{
	object_new = PyBaseObject_Type.tp_new;
	PyCompact_EmptyImpl = &k_empty_impl;
	PyCompactType_Type.tp_base = &PyType_Type;
	PyCompact_Type.tp_free = _PyObject_GC_Del;
	PyType_Ready(&PyCompactType_Type);
	PyType_Ready(&PyCompact_Type);

	Py_INCREF(&PyCompact_Type);
	PyModule_AddObject(CPsycoModule, "compact",
			   (PyObject*) &PyCompact_Type);
	Py_INCREF(&PyCompactType_Type);
	PyModule_AddObject(CPsycoModule, "compacttype",
			   (PyObject*) &PyCompactType_Type);
}
