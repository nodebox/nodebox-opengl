#include "piterobject.h"


DEFINEFN vinfo_t* PsycoSeqIter_NEW(PsycoObject* po, vinfo_t* seq)
{
	vinfo_t* zero;
	vinfo_t* result = vinfo_new(VirtualTime_New(&psyco_computed_seqiter));
	result->array = array_new(SEQITER_TOTAL);
	result->array->items[iOB_TYPE] =
		vinfo_new(CompileTime_New((long)(&PySeqIter_Type)));
	/* the iterator index is immediately run-time because it is
	   very likely to be unpromoted to run-time anyway */
	zero = psyco_vi_Zero();
	result->array->items[iSEQITER_IT_INDEX] = make_runtime_copy(po, zero);
	vinfo_decref(zero, po);
	/*result->array->items[SEQITER_IT_INDEX] =
		vinfo_new(CompileTime_New(0));*/
	result->array->items[iSEQITER_IT_SEQ] = seq;
	return result;
}


static vinfo_t* piter_getiter(PsycoObject* po, vinfo_t* v)
{
	vinfo_incref(v);
	return v;
}

static vinfo_t* piter_iternext(PsycoObject* po, vinfo_t* v)
{
	vinfo_t* seq;
	vinfo_t* index;
	vinfo_t* result;
	PyTypeObject* tp;

	seq = psyco_get_const(po, v, SEQITER_it_seq);
	if (seq == NULL)
		return NULL;

	tp = Psyco_NeedType(po, seq);
	if (tp == NULL)
		return NULL;

	index = psyco_get_field(po, v, SEQITER_it_index);
	if (index == NULL)
		return NULL;
	assert_nonneg(index);

	if (PyType_IsSubtype(tp, &PyList_Type)) {
		/* If the sequence is a list, explicitly ignore a
		   user-overridden __getitem__ slot.  This is what both
		   Python 2.2 and >=2.3 do (although they use a
		   different trick to reach that effect). */
		result = plist_item(po, seq, index);
	}
	else {
		result = PsycoSequence_GetItem(po, seq, index);
	}
	if (result == NULL) {
		vinfo_t* matches = PycException_Matches(po, PyExc_IndexError);
		if (runtime_NON_NULL_t(po, matches) == true) {
			PycException_SetVInfo(po, PyExc_StopIteration,
					      psyco_vi_None());
		}
	}
	else {
		/* very remotely potential incompatibility: when exhausted,
		   the internal iterator index is not incremented. Python
		   is not consistent in this respect. This could be an
		   issue if an iterator of a mutable object is not
		   immediately deleted when exhausted. Well, I guess that
		   muting an object we iterate over is generally considered
		   as DDIWWY (Don't Do It -- We Warned You.)
		   (Update: Python 2.5 is consistent, and does the same
		   as Psyco.) */
		vinfo_t* index_plus_1 = integer_add_i(po, index, 1, true);
		if (index_plus_1 == NULL ||
		    !psyco_put_field(po, v, SEQITER_it_index, index_plus_1)) {
			vinfo_decref(result, po);
			result = NULL;
		}
		vinfo_xdecref(index_plus_1, po);
	}
	vinfo_decref(index, po);
	return result;
}


static bool compute_seqiter(PsycoObject* po, vinfo_t* v)
{
	vinfo_t* seq;
	vinfo_t* index;
	vinfo_t* newobj;

	index = vinfo_getitem(v, iSEQITER_IT_INDEX);
	if (index == NULL)
		return false;

	seq = vinfo_getitem(v, iSEQITER_IT_SEQ);
	if (seq == NULL)
		return false;

	newobj = psyco_generic_call(po, PySeqIter_New,
				    CfReturnRef|CfPyErrIfNull, "v", seq);
	if (newobj == NULL)
		return false;

	/* Put the current index into the seq iterator.
	   This is done by putting the value directly in the
	   seqiterobject structure; it could be done by calling
	   PyIter_Next() n times but obviously that's not too
	   good a solution */
	if (!psyco_knowntobe(index, 0)) {
		if (!psyco_put_field(po, v, SEQITER_it_index, index)) {
			vinfo_decref(newobj, po);
			return false;
		}
	}

	/* Remove the SEQITER_IT_INDEX entry from v->array because it
	   is a mutable field now, and could be changed at any time by
	   anybody .*/
	psyco_forget_field(po, v, SEQITER_it_index);

	vinfo_move(po, v, newobj);
	return true;
}

DEFINEVAR source_virtual_t psyco_computed_seqiter;


INITIALIZATIONFN
void psy_iterobject_init(void)
{
        Psyco_DefineMeta(PySeqIter_Type.tp_iter, &piter_getiter);
        Psyco_DefineMeta(PySeqIter_Type.tp_iternext, &piter_iternext);

        /* iterator object are mutable;
           they must be forced out of virtual-time across function calls */
        INIT_SVIRTUAL_NOCALL(psyco_computed_seqiter, compute_seqiter, 1);
}
