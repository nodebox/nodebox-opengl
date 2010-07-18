 /***************************************************************/
/***            Psyco equivalent of iterobject.h               ***/
 /***************************************************************/

#ifndef _PSY_ITEROBJECT_H
#define _PSY_ITEROBJECT_H


#include "pobject.h"
#include "pabstract.h"


/* this structure not exported by iterobject.h */
typedef struct {
	PyObject_HEAD
	long      it_index;
	PyObject *it_seq;
} seqiterobject;

#define SEQITER_it_index  FMUT(DEF_FIELD(seqiterobject, long, it_index, OB_type))
#define SEQITER_it_seq    DEF_FIELD(seqiterobject, PyObject*, it_seq, \
						SEQITER_it_index)
#define iSEQITER_IT_INDEX FIELD_INDEX(SEQITER_it_index)
#define iSEQITER_IT_SEQ   FIELD_INDEX(SEQITER_it_seq)
#define SEQITER_TOTAL     FIELDS_TOTAL(SEQITER_it_seq)


/*********************************************************************/
 /* Virtual sequence iterators. Created if needed by PySeqIter_New(). */
EXTERNVAR source_virtual_t psyco_computed_seqiter;

/* !! consumes a ref on 'seq' */
EXTERNFN vinfo_t* PsycoSeqIter_NEW(PsycoObject* po, vinfo_t* seq);

PSY_INLINE vinfo_t* PsycoSeqIter_New(PsycoObject* po, vinfo_t* seq)
{
	vinfo_incref(seq);
	return PsycoSeqIter_NEW(po, seq);
}

#endif /* _PSY_ITEROBJECT_H */
