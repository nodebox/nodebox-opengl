#include "pstructmember.h"
#include "pstringobject.h"
#include "pintobject.h"
#include "pfloatobject.h"
#include "../pycodegen.h"


DEFINEFN
vinfo_t* PsycoMember_GetOne(PsycoObject* po, vinfo_t* addr, PyMemberDef* l)
{
	condition_code_t cc;
	vinfo_t* v;
	vinfo_t* w1;
	vinfo_t* w2;
	defield_t rdf;
	if (l->flags & READ_RESTRICTED)
		goto fallback;

	/* XXX add (some of) the missing types */
	switch (l->type) {
	case T_BYTE:  /* read a byte, extend it signed */
		rdf = FMUT(DEF_ARRAY(signed char, 0));
		break;
	case T_UBYTE:  /* read a byte, extend it unsigned */
		rdf = FMUT(UNSIGNED_ARRAY(unsigned char, 0));
		break;
	case T_SHORT:  /* read a short, extend it signed */
		rdf = FMUT(DEF_ARRAY(signed short, 0));
		break;
	case T_USHORT:  /* read a short, extend it unsigned */
		rdf = FMUT(UNSIGNED_ARRAY(unsigned short, 0));
		break;
	case T_INT:
	case T_UINT:
	case T_LONG:
	case T_ULONG:  /* read a long */
		/* XXX assumes sizeof(int) == sizeof(long) */
		rdf = FMUT(DEF_ARRAY(long, 0));
		break;
#if HAVE_FP_FN_CALLS
	case T_FLOAT:  /* read a long, turn it into a float */
		rdf = FMUT(DEF_ARRAY(float, 0));
		w1 = psyco_get_field_offset(po, addr, rdf, l->offset);
		if (w1 == NULL)
			return NULL;
		v = PsycoFloat_FromFloat(po, w1);
		vinfo_decref(w1, po);
		return v;
	case T_DOUBLE:  /* read two longs, turn them into a double */
		rdf = FMUT(DEF_ARRAY(double, 0));
		w1 = psyco_get_field_offset(po, addr, rdf, l->offset);
		if (w1 == NULL)
			return NULL;
		w2 = psyco_get_field_offset(po, addr, FIELD_PART2(rdf),
					    l->offset);
		if (w2 == NULL) {
			vinfo_decref(w1, po);
			return NULL;
		}
		v = PsycoFloat_FROM_DOUBLE(w1, w2);
		return v;
#endif
	case T_STRING:  /* read a char*, turn it into a string */
		rdf = FMUT(DEF_ARRAY(char*, 0));
		w1 = psyco_get_field_offset(po, addr, rdf, l->offset);
		if (w1 == NULL)
			return NULL;
		cc = integer_non_null(po, w1);
		if (cc == CC_ERROR) {
			vinfo_decref(w1, po);
			return NULL;
		}

		if (runtime_condition_t(po, cc)) {
			/* the char* is not NULL */
			v = psyco_generic_call(po, PyString_FromString,
					       CfReturnRef|CfPyErrIfNull,
					       "v", w1);
			if (v != NULL)
				Psyco_AssertType(po, v, &PyString_Type);
		}
		else {
			v = psyco_vi_None();
		}
		vinfo_decref(w1, po);
		return v;
	case T_STRING_INPLACE:  /* read an array of characters from the struct */
		w1 = integer_add_i(po, addr, l->offset, false);
		if (w1 == NULL)
			return NULL;
		v = psyco_generic_call(po, PyString_FromString,
				       CfReturnRef|CfPyErrIfNull,
				       "v", w1);
		if (v != NULL)
			Psyco_AssertType(po, v, &PyString_Type);
		vinfo_decref(w1, po);
		return v;
	case T_CHAR:  /* read a byte, turn it into a char */
		rdf = FMUT(UNSIGNED_ARRAY(unsigned char, 0));
		w1 = psyco_get_field_offset(po, addr, rdf, l->offset);
		if (w1 == NULL)
			return NULL;
		v = PsycoCharacter_New(w1);
		vinfo_decref(w1, po);
		return v;
	case T_OBJECT:  /* read a long, turn it into a PyObject with reference */
		rdf = FMUT(DEF_ARRAY(PyObject*, 0));
		v = psyco_get_field_offset(po, addr, rdf, l->offset);
		if (v == NULL)
			return NULL;
		cc = integer_non_null(po, v);
		if (cc == CC_ERROR) {
			vinfo_decref(v, po);
			return NULL;
		}

		if (runtime_condition_t(po, cc)) {
			/* 'v' contains a non-NULL value */
			need_reference(po, v);
		}
		else {
			/* 'v' contains NULL */
			vinfo_decref(v, po);
			v = psyco_vi_None();
		}
		return v;
#ifdef T_OBJECT_EX
	case T_OBJECT_EX:  /* same as T_OBJECT, exception if NULL */
		rdf = FMUT(DEF_ARRAY(PyObject*, 0));
		v = psyco_get_field_offset(po, addr, rdf, l->offset);
		if (v == NULL)
			return NULL;
		cc = integer_non_null(po, v);
		if (cc == CC_ERROR) {
			vinfo_decref(v, po);
			return NULL;
		}

		if (runtime_condition_t(po, cc)) {
			/* 'v' contains a non-NULL value */
			need_reference(po, v);
		}
		else {
			/* 'v' contains NULL */
			vinfo_decref(v, po);
			PycException_SetString(po, PyExc_AttributeError,
					       l->name);
			return NULL;
		}
		return v;
#endif
	default:
		goto fallback;
	}
	
	/* for integer fields of any size */
	v = psyco_get_field_offset(po, addr, rdf, l->offset);
	if (v != NULL)
		v = PsycoInt_FROM_LONG(v);
	return v;

  fallback:
	/* call the Python implementation for cases we cannot handle directy */
	return psyco_generic_call(po, PyMember_GetOne,
				  CfReturnRef|CfPyErrIfNull, "vl", addr, l);
}
