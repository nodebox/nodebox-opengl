 /***************************************************************/
/***                 General-purpose alarm module              ***/
 /***************************************************************/

#ifndef _ALARM_H
#define _ALARM_H


#include "psyco.h"


#define ALARM_FUNCTIONS   {"alarm",   psyco_new_alarm,   METH_VARARGS}

EXTERNFN PyObject* psyco_new_alarm(PyObject* dummy, PyObject* args);


#endif /* _ALARM_H */
