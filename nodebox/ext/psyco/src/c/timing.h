 /***************************************************************/
/***                   Measuring processor time                ***/
 /***************************************************************/

#ifndef _TIMING_H
#define _TIMING_H

#include "psyco.h"
#include "Python/pyver.h"


#define measure_is_zero(m)  ((m) == (time_measure_t) 0)


/***************************************************************/
/* Use the tick_counter field of the PyThreadState for timing  */

#define MEASURE_ALL_THREADS    1

typedef int time_measure_t;

PSY_INLINE time_measure_t get_measure(PyThreadState* tstate)
{
	int result = tstate->tick_counter;
	tstate->tick_counter = 0;
	return result;
}

/***************************************************************/


#endif /* _TIMING_H */
