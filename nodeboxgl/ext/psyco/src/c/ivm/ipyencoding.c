#include "ipyencoding.h"
#include "../pycodegen.h"


DEFINEFN
void decref_create_new_ref(PsycoObject* po, vinfo_t* w)
{
	psyco_incref_nv(po, w);
}

DEFINEFN
bool decref_create_new_lastref(PsycoObject* po, vinfo_t* w)
{
	bool could_eat = eat_reference(w);
	if (!could_eat) {
		/* in this case we must Py_INCREF() the object */
		psyco_incref_nv(po, w);
	}
	return could_eat;
}
