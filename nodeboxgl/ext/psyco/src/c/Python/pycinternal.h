 /***************************************************************/
/***         Includes Python internal headers                  ***/
 /***************************************************************/


#ifndef _PYCINTERNAL_H
#define _PYCINTERNAL_H

#include <opcode.h>


/* Post-2.2 versions of Python introduced the following more explicit names.
   XXX We should map the new names to the old ones if the new names do not
   XXX exist but how can we detect if this is needed?
   XXX Hacked by completely overriding the enum values with #defines. */

#define  PyCmp_IN		6
#define  PyCmp_NOT_IN		7
#define  PyCmp_IS		8
#define  PyCmp_IS_NOT		9
#define  PyCmp_EXC_MATCH	10


#endif /* _PYCINTERNAL_H */
