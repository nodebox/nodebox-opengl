#include "ptupleobject.h"


 /***************************************************************/
  /***   Virtual tuples                                        ***/

static source_virtual_t psyco_computed_tuple;

#if ALL_CHECKS
static void check_ituple(vinfo_t* v)
{
	int tuple_end = v->array->count;
	int l1 = CompileTime_Get(v->array->items[iFIX_SIZE]->source)->value;
	psyco_assert(tuple_end == iTUPLE_OB_ITEM + l1);
}
#else
# define check_ituple(v)    ;
#endif

static bool compute_tuple(PsycoObject* po, vinfo_t* v)
{
	int i, tuple_end;
	check_ituple(v);
	tuple_end = v->array->count;
	
	/* check whether all tuple objects are constant */
	for (i=iTUPLE_OB_ITEM; i<tuple_end; i++) {
		vinfo_t* vi = v->array->items[i];
		if (!is_compiletime(vi->source))
			break;  /* no */
	}
	if (i == tuple_end) {
		/* yes -- let's build a constant compile-time tuple */
		source_known_t* sk;
		PyObject* constant = PyTuple_New(tuple_end - iTUPLE_OB_ITEM);
		if (constant == NULL)
			OUT_OF_MEMORY();
		for (i=iTUPLE_OB_ITEM; i<tuple_end; i++) {
			PyObject* obj;
			sk = CompileTime_Get(v->array->items[i]->source);
			obj = (PyObject*) sk->value;
			Py_INCREF(obj);
			PyTuple_SET_ITEM(constant, i-iTUPLE_OB_ITEM, obj);
		}
		
		/* move the resulting non-virtual Python object back into 'v' */
		sk = sk_new((long) constant, SkFlagPyObj);
		v->source = CompileTime_NewSk(sk);
	}
	else {
		/* no -- code a call to PyTuple_New() */
		int tuple_len = tuple_end - iTUPLE_OB_ITEM;
		vinfo_t* tuple = psyco_generic_call(po, PyTuple_New,
                                                    CfReturnRef|CfPyErrIfNull,
                                                    "l", tuple_len);
		if (tuple == NULL)
			return false;

		/* write the storing of the objects in the tuple */
		for (i=0; i<tuple_len; i++) {
			vinfo_t* vi = PsycoTuple_GET_ITEM(v, i);
			if (!psyco_put_nth_field(po, tuple,
						 FMUT(FPYREF(TUPLE_ob_item)),
						 i, vi)) {
				vinfo_decref(tuple, po);
				return false;
			}
			/* new references are made by psyco_put_nth_field() */
		}
		/* move the resulting non-virtual Python object back into 'v' */
		vinfo_move(po, v, tuple);
	}
	return true;
}

static PyObject* direct_compute_tuple(vinfo_t* v, char* data)
{
	int i, tuple_end;
	PyObject* result;

	check_ituple(v);
	tuple_end = v->array->count;

	result = PyTuple_New(tuple_end - iTUPLE_OB_ITEM);
	if (result == NULL)
		return NULL;
	
	for (i=iTUPLE_OB_ITEM; i<tuple_end; i++) {
		PyObject* obj = direct_xobj_vinfo(v->array->items[i], data);
		if (obj == NULL) {
			Py_DECREF(result);
			return NULL;
		}
		PyTuple_SET_ITEM(result, i-iTUPLE_OB_ITEM, obj);
	}
	return result;
}

DEFINEFN
vinfo_t* PsycoTuple_New(int count, vinfo_t** source)
{
	int i;
	vinfo_t* r = vinfo_new(VirtualTime_New(&psyco_computed_tuple));
	r->array = array_new(iTUPLE_OB_ITEM + count);
	r->array->items[iOB_TYPE] =
		vinfo_new(CompileTime_New((long)(&PyTuple_Type)));
	r->array->items[iFIX_SIZE] = vinfo_new(CompileTime_New(count));
	if (source != NULL)
		for (i=0; i<count; i++) {
			vinfo_incref(source[i]);
			PsycoTuple_GET_ITEM(r, i) = source[i];
		}
	return r;
}


/* do not load a constant tuple into a vinfo_array_t if longer than: */
#define CT_TUPLE_LOAD_SIZE_LIMIT    15

DEFINEFN
int PsycoTuple_Load(vinfo_t* tuple)
{
	int size;
	/* if the tuple is virtual, then all items in its
	   vinfo_array_t are already filled */
	if (tuple->source == VirtualTime_New(&psyco_computed_tuple))
		size = tuple->array->count - iTUPLE_OB_ITEM;
	else if (is_compiletime(tuple->source)) {
		/* a constant tuple means constant tuple items */
		int i;
		PyObject* o = (PyObject*)(CompileTime_Get(tuple->source)->value);
		extra_assert(PyTuple_Check(o));
		size = PyTuple_GET_SIZE(o);
		if (tuple->array->count < iTUPLE_OB_ITEM + size) {
			if (/*not_too_much &&*/ size > CT_TUPLE_LOAD_SIZE_LIMIT)
				return -1;
			vinfo_array_grow(tuple, iTUPLE_OB_ITEM + size);
		}
		/* load the tuple into the vinfo_array_t */
		for (i=0; i<size; i++) {
			if (PsycoTuple_GET_ITEM(tuple, i) == NULL) {
				PyObject* item = PyTuple_GET_ITEM(o, i);
				source_known_t* sk = sk_new((long) item,
							    SkFlagPyObj);
				Py_INCREF(item);
				PsycoTuple_GET_ITEM(tuple, i) =
					vinfo_new(CompileTime_NewSk(sk));
			}
		}
	}
	else
		return -1;
	return size;
}

DEFINEFN
vinfo_t* PsycoTuple_Concat(PsycoObject* po, vinfo_t* v1, vinfo_t* v2)
{
	vinfo_t* result;
	int len1, len2;
	
	if (Psyco_VerifyType(po, v1, &PyTuple_Type) != true)
		return NULL;
	switch (Psyco_VerifyType(po, v2, &PyTuple_Type)) {
	case true:    /* 'v2' is a tuple */
		break;
	case false:   /* fallback */
		return psyco_generic_call(po,
					  PyTuple_Type.tp_as_sequence->sq_concat,
					  CfReturnRef|CfPyErrIfNull,
					  "vv", v1, v2);
	default:
		return NULL;
	}
	
	/* XXX a "virtual tuple concatenation" would be cool */
	len1 = PsycoTuple_Load(v1);  /* -1 if unknown */
	if (len1 == 0) {
		vinfo_incref(v2);
		return v2;
	}
	len2 = PsycoTuple_Load(v2);  /* -1 if unknown */
	if (len2 == 0) {
		vinfo_incref(v1);
		return v1;
	}

	if (len1 == -1 || len2 == -1) {
		/* cannot do it now. Fall back. */
		result = psyco_generic_call(po,
					PyTuple_Type.tp_as_sequence->sq_concat,
					CfReturnRef|CfPyErrIfNull,
					"vv", v1, v2);
		if (result == NULL)
			return NULL;

		/* the result is a tuple */
                Psyco_AssertType(po, result, &PyTuple_Type);
	}
	else {
		int i;
		result = PsycoTuple_New(len1+len2, NULL);
		for (i=0; i<len1; i++) {
			vinfo_t* v = PsycoTuple_GET_ITEM(v1, i);
			vinfo_incref(v);
			PsycoTuple_GET_ITEM(result, i) = v;
		}
		for (i=0; i<len2; i++) {
			vinfo_t* v = PsycoTuple_GET_ITEM(v2, i);
			vinfo_incref(v);
			PsycoTuple_GET_ITEM(result, len1 + i) = v;
		}
	}
	return result;
}


 /***************************************************************/
  /*** tuple objects meta-implementation                       ***/

static vinfo_t* ptuple_item(PsycoObject* po, vinfo_t* a, vinfo_t* i)
{
	condition_code_t cc;
	vinfo_t* vlen;

	vlen = psyco_get_const(po, a, FIX_size);
	if (vlen == NULL)
		return NULL;
	
	cc = integer_cmp(po, i, vlen, Py_GE|COMPARE_UNSIGNED);
	if (cc == CC_ERROR)
		return NULL;

	if (runtime_condition_f(po, cc)) {
		PycException_SetString(po, PyExc_IndexError,
				       "tuple index out of range");
		return NULL;
	}

	return psyco_get_field_array(po, a, FPYREF(TUPLE_ob_item), i);
}


INITIALIZATIONFN
void psy_tupleobject_init(void)
{
	PyMappingMethods *mm;
	PySequenceMethods *m = PyTuple_Type.tp_as_sequence;
	Psyco_DefineMeta(m->sq_length, psyco_generic_immut_ob_size);
	Psyco_DefineMeta(m->sq_item, ptuple_item);
        Psyco_DefineMeta(m->sq_concat, PsycoTuple_Concat);

	mm = PyString_Type.tp_as_mapping;
	if (mm) {  /* Python >= 2.3 */
		Psyco_DefineMeta(mm->mp_subscript, psyco_generic_subscript);
	}

        INIT_SVIRTUAL(psyco_computed_tuple, compute_tuple,
		      direct_compute_tuple,
                      (-1 << iTUPLE_OB_ITEM),  /* sign bit of bitfield will
                                                  be extended indefinitely */
                      NW_TUPLES_NORMAL, NW_TUPLES_FUNCALL);
}
