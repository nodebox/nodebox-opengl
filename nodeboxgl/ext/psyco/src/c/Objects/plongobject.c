#include "plongobject.h"


DEFINEFN
vinfo_t* PsycoLong_AsLong(PsycoObject* po, vinfo_t* v)
{
	/* XXX implement me */
	return psyco_generic_call(po, PyLong_AsLong,
				  CfReturnNormal|CfPyErrCheckMinus1,
				  "v", v);
}

static void cimpl_lng_as_double(PyObject* o, double* result)
{
	*result = PyLong_AsDouble(o);
}

DEFINEFN
bool PsycoLong_AsDouble(PsycoObject* po, vinfo_t* v, vinfo_t** vd1, vinfo_t** vd2)
{
	/* XXX implement me */
	vinfo_array_t* result;
	result = array_new(2);
	if (psyco_generic_call(po, cimpl_lng_as_double,
				  CfPyErrCheck,
				  "va", v, result) == NULL) {
		array_release(result);
		return false;
	}
        *vd1 = result->items[0];
        *vd2 = result->items[1]; 
	array_release(result);
	return true;
}


/* XXX this assumes that operations between longs always return a long.
   There are hints that this might change in future releases of Python. */
#define RETLONG(arity, cname, slotname)						\
	DEF_KNOWN_RET_TYPE_##arity(cname,					\
				   PyLong_Type.tp_as_number->slotname,		\
				   (arity)==1 ? (CfReturnRef|CfPyErrIfNull) :	\
				        (CfReturnRef|CfPyErrNotImplemented),	\
				   &PyLong_Type)

/* Python 2.2's long_mul() tries to be clever about 'sequence * long' */
#define SANE_CONVERT_BINOP  (PY_VERSION_HEX >= 0x02030000)   /* 2.3 */

RETLONG(2,	plong_add,		nb_add)
RETLONG(2,	plong_sub,		nb_subtract)
#if SANE_CONVERT_BINOP
RETLONG(2,	plong_mul,		nb_multiply)
#endif
RETLONG(2,	plong_classic_div,	nb_divide)
RETLONG(2,	plong_mod,		nb_remainder)
RETLONG(3,	plong_pow,		nb_power)
RETLONG(1,	plong_neg,		nb_negative)
RETLONG(1,	plong_pos,		nb_positive)
RETLONG(1,	plong_abs,		nb_absolute)
RETLONG(1,	plong_invert,		nb_invert)
RETLONG(2,	plong_lshift,		nb_lshift)
RETLONG(2,	plong_rshift,		nb_rshift)
RETLONG(2,	plong_and,		nb_and)
RETLONG(2,	plong_xor,		nb_xor)
RETLONG(2,	plong_or,		nb_or)
RETLONG(2,	plong_div,		nb_floor_divide)
     /*RETFLOAT(2,	plong_true_divide,	nb_true_divide)  XXX-implement*/

#undef RETLONG


INITIALIZATIONFN
void psy_longobject_init(void)
{
	PyNumberMethods *m = PyLong_Type.tp_as_number;

	Psyco_DefineMeta(m->nb_add,		plong_add);
	Psyco_DefineMeta(m->nb_subtract,	plong_sub);
#if SANE_CONVERT_BINOP
	Psyco_DefineMeta(m->nb_multiply,	plong_mul);
#endif
	Psyco_DefineMeta(m->nb_divide,		plong_classic_div);
	Psyco_DefineMeta(m->nb_remainder,	plong_mod);
	Psyco_DefineMeta(m->nb_power,		plong_pow);
	Psyco_DefineMeta(m->nb_negative,	plong_neg);
	Psyco_DefineMeta(m->nb_positive,	plong_pos);
	Psyco_DefineMeta(m->nb_absolute,	plong_abs);
	Psyco_DefineMeta(m->nb_invert,		plong_invert);
	Psyco_DefineMeta(m->nb_lshift,		plong_lshift);
	Psyco_DefineMeta(m->nb_rshift,		plong_rshift);
	Psyco_DefineMeta(m->nb_and,		plong_and);
	Psyco_DefineMeta(m->nb_xor,		plong_xor);
	Psyco_DefineMeta(m->nb_or,		plong_or);
	Psyco_DefineMeta(m->nb_floor_divide,	plong_div);
/* Psyco_DefineMeta(m->nb_true_divide,	plong_true_divide);  XXX-implement*/
}
