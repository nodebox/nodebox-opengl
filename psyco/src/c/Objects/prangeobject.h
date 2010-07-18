 /***************************************************************/
/***            Psyco equivalent of rangeobject.h              ***/
 /***************************************************************/

#ifndef _PSY_RANGEOBJECT_H
#define _PSY_RANGEOBJECT_H


#include "pobject.h"
#include "pabstract.h"
#include "plistobject.h"


/* currently step == 1 only */
/* The following functions *consume* a reference to start and len ! */

/* for xrange() */
EXTERNFN vinfo_t* PsycoXRange_NEW(PsycoObject* po, vinfo_t* start, vinfo_t* len);
/* for range() */
EXTERNFN vinfo_t* PsycoListRange_NEW(PsycoObject* po, vinfo_t* start, vinfo_t* len);


 /***************************************************************/
  /***   Virtual list range objects (not for xrange)           ***/

#define RANGE_LEN           iVAR_SIZE       /* for virtual range() only */
#define RANGE_START         LIST_TOTAL      /*       "                  */
/*#define RANGE_STEP        (RANGE_START+1)  *       "                  */
#define RANGE_TOTAL       /*(RANGE_STEP+1)*/    (RANGE_START+1)
/* XXX no support for steps currently. Needs implementation of division to
   figure out the length. */

EXTERNVAR source_virtual_t psyco_computed_listrange;


#endif /* _PSY_RANGEOBJECT_H */
