#include "../psyco.h"
#include "../Objects/pabstract.h"
#include "../Objects/pintobject.h"
#include "../Objects/pfloatobject.h"
#include "../Objects/pstringobject.h"
#include "../Objects/ptupleobject.h"


/***************************************************************/

/* the following two variables are set by the initialization function
   to point to private things in arraymodule.c */
static PyCFunction cimpl_array = NULL;   /* ptr to C impl of array.array() */
static PyTypeObject* arraytype;          /* array.ArrayType */


/* declarations copied from arraymodule.c */
struct arrayobject; /* Forward */
struct arraydescr {
	int typecode;
	int itemsize;
	PyObject * (*getitem)(struct arrayobject *, int);
	int (*setitem)(struct arrayobject *, int, PyObject *);
};
typedef struct arrayobject {
	PyObject_HEAD
	int ob_size;
	char *ob_item;
#if HAVE_arrayobject_allocated
	int allocated;
#endif
	struct arraydescr *ob_descr;
} arrayobject;


#define ARRAY_ob_item     FMUT(DEF_FIELD(arrayobject, char*, ob_item, VAR_size))
#define ARRAY_ob_descr    DEF_FIELD(arrayobject, struct arraydescr*, \
				    ob_descr, ARRAY_ob_item)
#define iARRAY_OB_ITEM    FIELD_INDEX(ARRAY_ob_item)
#define iARRAY_OB_DESCR   FIELD_INDEX(ARRAY_ob_descr)
#define ARRAY_TOTAL       FIELDS_TOTAL(ARRAY_ob_descr)


/* meta-implementation of some getitem() and setitem() functions.
   Our meta-implementations of setitem() are never called with a run-time
   index equal to -1; to do the equivalent of the array module's object
   type checking, you must call setitem() with a *compile-time* value of -1. */

PSY_INLINE vinfo_t* generic_getitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi,
				defield_t rdf)
{
	vinfo_t* result;
	vinfo_t* ob_item;
	
	ob_item = psyco_get_field(po, ap, ARRAY_ob_item);
	if (ob_item == NULL)
		return NULL;

	result = psyco_get_field_array(po, ob_item, rdf, vi);
	vinfo_decref(ob_item, po);
	return result;
}

static vinfo_t* integral_getitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi,
				 defield_t rdf)
{
	vinfo_t* num = generic_getitem(po, ap, vi, rdf);
	if (num != NULL) {
		return PsycoInt_FROM_LONG(num);
	}
	else
		return NULL;
}

static vinfo_t* p_c_getitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi)
{
        defield_t rdf = FMUT(UNSIGNED_ARRAY(unsigned char, 0));
	vinfo_t* chr = generic_getitem(po, ap, vi, rdf);
	if (chr != NULL) {
		vinfo_t* result = PsycoCharacter_New(chr);
		vinfo_decref(chr, po);
		return result;
	}
	else
		return NULL;
}

static vinfo_t* p_b_getitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi) {
	return integral_getitem(po, ap, vi,
				FMUT(DEF_ARRAY(signed char, 0)));
}

static vinfo_t* p_BB_getitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi) {
	return integral_getitem(po, ap, vi,
				FMUT(UNSIGNED_ARRAY(unsigned char, 0)));
}

static vinfo_t* p_h_getitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi) {
	return integral_getitem(po, ap, vi,
				FMUT(DEF_ARRAY(signed short, 0)));
}

static vinfo_t* p_HH_getitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi) {
	return integral_getitem(po, ap, vi,
				FMUT(UNSIGNED_ARRAY(unsigned short, 0)));
}

static vinfo_t* p_l_getitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi) {
	return integral_getitem(po, ap, vi,
				FMUT(DEF_ARRAY(long, 0)));
}

#if HAVE_FP_FN_CALLS
static vinfo_t* p_f_getitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi)
{
	defield_t rdf = FMUT(DEF_ARRAY(float, 0));
	vinfo_t* fval = generic_getitem(po, ap, vi, rdf);
	if (fval != NULL) {
		vinfo_t* result = PsycoFloat_FromFloat(po, fval);
		vinfo_decref(fval, po);
		return result;
	}
	else
		return NULL;
}

static vinfo_t* p_d_getitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi)
{
	vinfo_t* ob_item;
	vinfo_t* fval1;
	vinfo_t* fval2;
	defield_t rdf = FMUT(DEF_ARRAY(double, 0));

	ob_item = psyco_get_field(po, ap, ARRAY_ob_item);
	if (ob_item == NULL)
		return NULL;

	fval1 = psyco_get_field_array(po, ob_item, rdf, vi);
	if (fval1 == NULL) {
		vinfo_decref(ob_item, po);
		return NULL;
	}
	fval2 = psyco_get_field_array(po, ob_item, FIELD_PART2(rdf), vi);
	vinfo_decref(ob_item, po);
	if (fval2 == NULL) {
		vinfo_decref(fval1, po);
		return NULL;
	}

	return PsycoFloat_FROM_DOUBLE(fval1, fval2);
}
#else
#  define p_f_getitem   NULL
#  define p_d_getitem   NULL
#endif


PSY_INLINE bool generic_setitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi,
			    vinfo_t* value, defield_t rdf)
{
	bool result;
	vinfo_t* ob_item;
	
	ob_item = psyco_get_field(po, ap, ARRAY_ob_item);
	if (ob_item == NULL)
		return false;

	result = psyco_put_field_array(po, ob_item, rdf, vi, value);
	vinfo_decref(ob_item, po);
	return result;
}

static bool integral_setitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi,
			     vinfo_t* v, long lowbound, long highbound,
			     defield_t rdf)
{
	bool result;
	vinfo_t* value = PsycoInt_AsLong(po, v);
	if (value == NULL) {
		/* XXX translate TypeError("an integer is required")
			    into TypeError("array item must be integer") */
		return false;
	}

	switch (runtime_in_bounds(po, value, lowbound, highbound)) {
	case 0:
		/* XXX build the correct error message */
		PycException_SetString(po, PyExc_OverflowError,
				       "array item is out of bounds");
		result = false;
		break;
	case 1:
		result = generic_setitem(po, ap, vi, value, rdf);
		break;
	default:
		result = false;
		break;
	}
	vinfo_decref(value, po);
	return result;
}

static bool p_c_setitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi, vinfo_t* v)
{
	vinfo_t* value;
	if (!PsycoCharacter_Ord(po, v, &value))
		return false;

	if (value != NULL) {
		/* 'v' is really a string of size 1 */
		defield_t rdf = FMUT(UNSIGNED_ARRAY(char, 0));
		bool result = generic_setitem(po, ap, vi, value, rdf);
		vinfo_decref(value, po);
		return result;
	}
	PycException_SetString(po, PyExc_TypeError,
			       "array item must be char");
	return false;
}

static bool p_b_setitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi, vinfo_t* v) {
	return integral_setitem(po, ap, vi, v, -128, 127,
				FMUT(DEF_ARRAY(char, 0)));
}

static bool p_BB_setitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi, vinfo_t* v) {
	return integral_setitem(po, ap, vi, v, 0, UCHAR_MAX,
				FMUT(UNSIGNED_ARRAY(char, 0)));
}

static bool p_h_setitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi, vinfo_t* v) {
	return integral_setitem(po, ap, vi, v, SHRT_MIN, SHRT_MAX,
				FMUT(DEF_ARRAY(short, 0)));
}

static bool p_HH_setitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi, vinfo_t* v) {
	return integral_setitem(po, ap, vi, v, 0, USHRT_MAX,
				FMUT(UNSIGNED_ARRAY(short, 0)));
}

static bool p_l_setitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi, vinfo_t* v) {
	return integral_setitem(po, ap, vi, v, LONG_MIN, LONG_MAX,
				FMUT(DEF_ARRAY(long, 0)));
}

#if HAVE_FP_FN_CALLS
#define p_f_setitem  NULL
/*
static bool p_f_setitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi, vinfo_t* v) {
	XXX implement PsycoFloat_AsFloat() XXX
}*/

static bool p_d_setitem(PsycoObject* po, vinfo_t* ap, vinfo_t* vi, vinfo_t* v) {
	vinfo_t* w1;
	vinfo_t* w2;
	bool result;
	vinfo_t* ob_item;
	defield_t rdf = FMUT(DEF_ARRAY(double, 0));

	if (!PsycoFloat_AsDouble(po, v, &w1, &w2))
		return false;
	
	ob_item = psyco_get_field(po, ap, ARRAY_ob_item);
	if (ob_item == NULL)
		result = false;
	else {
		result = psyco_put_field_array(po, ob_item, rdf, vi, w1) &&
		    psyco_put_field_array(po, ob_item, FIELD_PART2(rdf), vi, w2);
		vinfo_decref(ob_item, po);
	}
        vinfo_decref(w2, po);
        vinfo_decref(w1, po);
	return result;
}
#else
#  define p_f_setitem   NULL
#  define p_d_setitem   NULL
#endif


/* list of meta-implementations of descriptor-specific getitem() and setitem() */
struct metadescr_s {
	int typecode;
	vinfo_t* (*meta_getitem) (PsycoObject*, vinfo_t*, vinfo_t*);
	bool (*meta_setitem) (PsycoObject*, vinfo_t*, vinfo_t*, vinfo_t*);
	struct arraydescr* base;
};

static struct metadescr_s metadescriptors[] = {
	{'c', p_c_getitem, p_c_setitem},
	{'b', p_b_getitem, p_b_setitem},
	{'B', p_BB_getitem, p_BB_setitem},
#ifdef Py_USING_UNICODE
	/* XXX */
#endif
	{'h', p_h_getitem, p_h_setitem},
	{'H', p_HH_getitem, p_HH_setitem},
#if SIZEOF_INT==SIZEOF_LONG
#  define p_i_getitem   p_l_getitem
#  define p_i_setitem   p_l_setitem
	{'i', p_i_getitem, p_i_setitem},
	/*#  define p_II_getitem  p_l_getitem
	  #  define p_II_setitem  p_l_setitem
	  {'I', p_II_getitem, p_II_setitem},*/
#endif
	{'l', p_l_getitem, p_l_setitem},
	/*#define p_LL_getitem  p_l_getitem
	  #define p_LL_setitem  p_l_setitem
	  {'L', p_LL_getitem, p_LL_setitem},*/
	{'f', p_f_getitem, p_f_setitem},
	{'d', p_d_getitem, p_d_setitem},
	{'\0', NULL, NULL} /* Sentinel */
};


/* meta-implementation of array_item */
static vinfo_t* parray_item(PsycoObject* po, vinfo_t* ap, vinfo_t* vi)
{
	condition_code_t cc;
	vinfo_t* vlen;
	struct arraydescr* d;
	long dlong;

	/* get the ob_descr field of 'ap' and promote it to compile-time */
	vinfo_t* vdescr = psyco_get_const(po, ap, ARRAY_ob_descr);
	if (vdescr == NULL)
		return NULL;
	dlong = psyco_atcompiletime(po, vdescr);
	if (dlong == -1) {
		/* a pointer cannot be -1, so we know it must be an exception */
		extra_assert(PycException_Occurred(po));
		return NULL;
	}
	d = (struct arraydescr*) dlong;

	/* check that the index is within range */
	vlen = psyco_get_field(po, ap, VAR_size);
	if (vlen == NULL)
		return NULL;
	
	cc = integer_cmp(po, vi, vlen, Py_GE|COMPARE_UNSIGNED);
        vinfo_decref(vlen, po);
	if (cc == CC_ERROR)
		return NULL;

	if (runtime_condition_f(po, cc)) {
		PycException_SetString(po, PyExc_IndexError,
				       "array index out of range");
		return NULL;
	}

	/* call the item getter or its meta-implementation */
	return Psyco_META2(po, d->getitem, CfReturnRef|CfPyErrIfNull,
			   "vv", ap, vi);
}

static bool parray_ass_item(PsycoObject* po, vinfo_t* ap, vinfo_t* vi,vinfo_t* v)
{
	vinfo_t* vdescr;
	condition_code_t cc;
	vinfo_t* vlen;
	struct arraydescr* d;
	long dlong;

	if (v == NULL) {
		/* XXX implement item deletion */
		return psyco_generic_call(po, arraytype->tp_as_sequence->
					  sq_ass_item,
					  CfNoReturnValue|CfPyErrIfNonNull,
					  "vvl", ap, vi, (long) NULL) != NULL;
	}
	
	/* get the ob_descr field of 'ap' and promote it to compile-time */
	vdescr = psyco_get_const(po, ap, ARRAY_ob_descr);
	if (vdescr == NULL)
		return false;
	dlong = psyco_atcompiletime(po, vdescr);
	if (dlong == -1) {
		/* a pointer cannot be -1, so we know it must be an exception */
		extra_assert(PycException_Occurred(po));
		return false;
	}
	d = (struct arraydescr*) dlong;

	/* check that the index is within range */
	vlen = psyco_get_field(po, ap, VAR_size);
	if (vlen == NULL)
		return false;
	
	cc = integer_cmp(po, vi, vlen, Py_GE|COMPARE_UNSIGNED);
        vinfo_decref(vlen, po);
	if (cc == CC_ERROR)
		return false;

	if (runtime_condition_f(po, cc)) {
		PycException_SetString(po, PyExc_IndexError,
				       "array assignment index out of range");
		return false;
	}

	/* call the item setter or its meta-implementation */
	return Psyco_META3(po, d->setitem, CfNoReturnValue|CfPyErrIfNonNull,
			   "vvv", ap, vi, v) != NULL;
}


/* array creation: we know the result is of type ArrayType. */
DEF_KNOWN_RET_TYPE_2(pa_array, cimpl_array, CfReturnRef|CfPyErrIfNull, arraytype)

static vinfo_t* parray_new(PsycoObject* po, PyTypeObject* type,
			   vinfo_t* varg, vinfo_t* vkw)
{
	/* In this version we also decode a constant-time
	   description character. */
	vinfo_t* result = psyco_generic_call(po, arraytype->tp_new,
					     CfReturnRef|CfPyErrIfNull,
					     "lvv", type, varg, vkw);
	if (result != NULL) {
		vinfo_t* firstarg;
		PyObject* a;
		struct metadescr_s* descr;
		char code;
		
		if (PsycoTuple_Load(varg) < 1) goto cannot_decode;
		firstarg = PsycoTuple_GET_ITEM(varg, 0);
		if (!is_compiletime(firstarg->source)) goto cannot_decode;
		
		a = (PyObject*) CompileTime_Get(firstarg->source)->value;
		if (!PyString_Check(a) || PyString_GET_SIZE(a) != 1)
			goto cannot_decode;
		
		code = *PyString_AS_STRING(a);
		for (descr=metadescriptors; descr->typecode!=0; descr++) {
			if (descr->typecode == code) {
				if (descr->base != NULL) {
					psyco_assert_field(po, result,
							   ARRAY_ob_descr,
							   (long) descr->base);
				}
				break;
			}
		}
		
	cannot_decode:
		Psyco_AssertType(po, result, type);
	}
	return result;
}

/***************************************************************/


INITIALIZATIONFN
void psyco_initarray(void)
{
	PyObject* md = Psyco_DefineMetaModule("array");
	PyObject* arrayobj;
	struct metadescr_s* descr;
	PySequenceMethods* m;
	PyMappingMethods *mm;

	if (md == NULL)
		return;
	
	/* get array.array and array.ArrayType */
	arrayobj = Psyco_GetModuleObject(md, "array", NULL);
	arraytype = (PyTypeObject*)
		Psyco_GetModuleObject(md, "ArrayType", &PyType_Type);

	/* bail out if not found */
	if (arrayobj == NULL || arraytype == NULL) {
		Py_DECREF(md);
		return;
	}

	m = arraytype->tp_as_sequence;
	Psyco_DefineMeta(m->sq_length,   psyco_generic_mut_ob_size);
	Psyco_DefineMeta(m->sq_item,     parray_item);
	Psyco_DefineMeta(m->sq_ass_item, parray_ass_item);

	mm = arraytype->tp_as_mapping;
	if (mm) {  /* Python >= 2.3 */
		Psyco_DefineMeta(mm->mp_subscript, psyco_generic_subscript);
		Psyco_DefineMeta(mm->mp_ass_subscript,
				 psyco_generic_ass_subscript);
	}
	
	/* map array.array() to its meta-implementation pa_array() */
	cimpl_array = Psyco_DefineModuleC(md, "array", METH_VARARGS,
					  &pa_array, &parray_new);

	for (descr=metadescriptors; descr->typecode!=0; descr++) {
		/* There seem to be no better way to get Python's
		   original array descriptors than to create dummy
		   arrays */
		PyObject* array = PyObject_CallFunction(arrayobj, "c",
						(char) descr->typecode);
		if (!array) {
			PyErr_Clear();
			debug_printf(1, ("init: cannot create an array of "
                                         "typecode '%c'\n",
                                         (char)descr->typecode));
		}
		else {
			struct arraydescr* d = ((arrayobject*) array)->ob_descr;
			if (descr->meta_getitem)
				Psyco_DefineMeta(d->getitem,descr->meta_getitem);
			if (descr->meta_setitem)
				Psyco_DefineMeta(d->setitem,descr->meta_setitem);
			descr->base = d;
			Py_DECREF(array);
		}
	}
	Py_DECREF(md);
}
