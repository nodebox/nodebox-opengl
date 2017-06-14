#include "cstruct.h"


DEFINEFN
PyObject* PyCStruct_New(size_t size, destructor d)
{
	cstruct_header_t* cs;
	cs = (cstruct_header_t*) PyObject_Malloc(size);
	if (cs == NULL)
		OUT_OF_MEMORY();
	PyObject_INIT(cs, &PyCStruct_Type);
	cs->cs_destructor = d;
	cs->cs_key = NULL;
	return (PyObject*) cs;
}

static void cstruct_dealloc(cstruct_header_t* cs)
{
	if (cs->cs_destructor != NULL)
		cs->cs_destructor((PyObject*) cs);
	Py_XDECREF(cs->cs_key);
	PyObject_Del((PyObject*) cs);
}

static long cstruct_hash(cstruct_header_t* cs)
{
	/* loosing high bits is fine. This can't be -1 */
	if (cs->cs_key == NULL)
		return (long)cs;
	else
		return (long)cs->cs_key;
}

static PyObject* cstruct_richcmp(cstruct_header_t* o1, cstruct_header_t* o2,
				 int op)
{
	int c;
	PyObject* result;
	char* k1 = o1->cs_key ? (char*) o1->cs_key : (char*) o1;
	char* k2 = o2->cs_key ? (char*) o2->cs_key : (char*) o2;
	switch (op) {
	case Py_EQ:	c = k1 == k2;	break;
	case Py_NE:	c = k1 != k2;	break;
	case Py_LT:	c = k1 <  k2;	break;
	case Py_LE:	c = k1 <= k2;	break;
	case Py_GT:	c = k1 >  k2;	break;
	case Py_GE:	c = k1 >= k2;	break;
	default:
		Py_INCREF(Py_NotImplemented);
		return Py_NotImplemented;
	}
	result = c ? Py_True : Py_False;
	Py_INCREF(result);
	return result;
}


DEFINEVAR
PyTypeObject PyCStruct_Type = {
	PyObject_HEAD_INIT(NULL)
	0,					/*ob_size*/
	"CStruct",				/*tp_name*/
	sizeof(cstruct_header_t) /* + ??? */,	/*tp_basicsize*/
	0,					/*tp_itemsize*/
	/* methods */
	(destructor)cstruct_dealloc,		/*tp_dealloc*/
	0,					/*tp_print*/
	0,					/*tp_getattr*/
	0,					/*tp_setattr*/
	0,					/*tp_compare*/
	0,					/*tp_repr*/
	0,					/*tp_as_number*/
	0,					/*tp_as_sequence*/
	0,					/*tp_as_mapping*/
	(hashfunc)cstruct_hash,			/*tp_hash*/
	0,					/*tp_call*/
	0,					/*tp_str*/
	0,					/*tp_getattro*/
	0,					/*tp_setattro*/
	0,					/*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT,			/*tp_flags*/
	0,					/*tp_doc*/
	0,					/*tp_traverse*/
	0,					/*tp_clear*/
	(richcmpfunc)cstruct_richcmp,		/*tp_richcompare*/
};


INITIALIZATIONFN
void psyco_cstruct_init(void)
{
	PyCStruct_Type.ob_type = &PyType_Type;
}
