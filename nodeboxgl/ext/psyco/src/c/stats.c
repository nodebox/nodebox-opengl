#include "stats.h"
#include "mergepoints.h"
#include "profile.h"
#include "cstruct.h"
#include <compile.h>
#include <frameobject.h>


static PyObject* codestats_dict;  /* dict of {cs: cs} */


static void PyCodeStats_dealloc(PyCodeStats* cs)
{
	Py_XDECREF(cs->st_codebuf);
	Py_XDECREF(cs->st_globals);
	Py_XDECREF(cs->st_mergepoints);
}

DEFINEFN
PyCodeStats* PyCodeStats_Get(PyCodeObject* co)
{
	PyCodeStats* cs;
	RECLIMIT_SAFE_ENTER();
	cs = (PyCodeStats*) PyCStruct_DictGet(codestats_dict, (PyObject*) co);
	if (cs == NULL) {
		cs = PyCStruct_NEW(PyCodeStats, PyCodeStats_dealloc);

		Py_INCREF(co);
		cs->cs_key = (PyObject*) co;
		cs->st_charge = 0.0f;
		cs->st_mergepoints = NULL;
                cs->st_codebuf = NULL;
                cs->st_globals = NULL;

		if (PyDict_SetItem(codestats_dict, (PyObject*) cs,
				   (PyObject*) cs) < 0)
			OUT_OF_MEMORY();
		Py_DECREF(cs);  /* two references left in codestats_dict */
	}
	RECLIMIT_SAFE_LEAVE();
	return cs;
}

DEFINEFN
PyCodeStats* PyCodeStats_MaybeGet(PyCodeObject* co)
{
	PyCodeStats* cs;
	RECLIMIT_SAFE_ENTER();
	cs = (PyCodeStats*) PyCStruct_DictGet(codestats_dict, (PyObject*) co);
	RECLIMIT_SAFE_LEAVE();
	return cs;
}


/***************************************************************/
 /***   Collecting statistics                                 ***/

/* to give recently executed code objects more chances to be compiled,
   be simulate a "decay" of the st_charge associated with them.
   We don't actually lower their st_charge; instead, we make their
   value comparatively less important by increasing how much charge
   the currently executing code objects will recieve. */

static double charge_total         = 0.0;    /* total of all st_charges */
static float charge_prelimit       = 0.0;    /* optimization only */
static float charge_watermark      = 1.0f;   /* see below */
static float charge_unit           = 1E-38f; /* current unit of charge */
static float charge_parent2        = 1.0f;   /* see below */
static PyObject* charge_callback   = NULL;

/* When a single PyCodeStats.st_charge reaches
   'charge_total * charge_watermark', the callback function is called
   (and typically, compilation starts).  So charge_watermark gives the
   charge limit expressed in a fraction of the total charge.  This is
   why decaying is important: a single function can reach a relatively
   high percentage of the total charge only if the other functions'
   charge decay quickly enough.

   'charge_total' is a double because it is an accumulator and its
   value must be accurate. */

/* the parent of a running frame is also charged, and its own parent too,
   and so on, but the charge is less and less.  Satistically, each parent
   is charged only 'charge_parent2 / 2' as much as its child. */


DEFINEFN
PyObject* psyco_stats_read(char* name)
{
	if (strcmp(name, "total") == 0)
		return PyFloat_FromDouble(         charge_total);
	if (strcmp(name, "unit") == 0)
		return PyFloat_FromDouble((double) charge_unit);
	if (strcmp(name, "watermark") == 0)
		return PyFloat_FromDouble((double) charge_watermark);
	if (strcmp(name, "parent2") == 0)
		return PyFloat_FromDouble((double) charge_parent2);
	
	PyErr_SetString(PyExc_ValueError, "no such readable parameter");
	return NULL;
}

static int writeobj_with_ref(PyObject* obj, PyObject** target)
{
	PyObject* prev = *target;
	if (obj == Py_None)
		obj = NULL;
	else
		Py_INCREF(obj);
	*target = obj;
	Py_XDECREF(prev);
	return 1;
}

DEFINEFN
bool psyco_stats_write(PyObject* args, PyObject* kwds)
{
	static char *kwlist[] = {"unit",
				 "total",
				 "watermark",
				 "parent2",
				 "callback",
				 "logger", 0};
	charge_prelimit = 0.0f;
	return PyArg_ParseTupleAndKeywords(args, kwds, "|fdffO&O&", kwlist,
					   &charge_unit,
					   &charge_total,
					   &charge_watermark,
					   &charge_parent2,
		       &writeobj_with_ref, &charge_callback,
		       &writeobj_with_ref, &psyco_logger);
}


/* very cheap very weak pseudo-random number generator */
static unsigned int c_seek = 1;
PSY_INLINE unsigned int c_random(void)
{
	return (c_seek = c_seek * 9);
}


#if VERBOSE_STATS
# define STATLINES  10
static void stats_dump(void)
{
	float top[STATLINES];
	char* top_names[STATLINES];
	int i, j, k=0;
	PyObject *key, *value;
	for (i=0; i<STATLINES; i++)
		top[i] = -1.0f;
	
	while (PyDict_Next(codestats_dict, &k, &key, &value)) {
		PyCodeStats* cs = (PyCodeStats*) key;
		PyCodeObject* co;
		extra_assert(PyCStruct_Check(key));
		extra_assert(PyCode_Check(cs->cs_key));
		co = (PyCodeObject*) cs->cs_key;
		for (i=0; i<STATLINES; i++) {
			if (cs->st_charge > top[i]) {
				for (j=STATLINES-1; j>i; j--) {
					top      [j] = top      [j-1];
					top_names[j] = top_names[j-1];
				}
				top      [i] = cs->st_charge;
				top_names[i] = PyCodeObject_NAME(co);
				break;
			}
		}
	}
	for (i=0; i<STATLINES; i++) {
		if (top[i] < 0.0f)
			break;
		stats_printf(("stats:  #%d %18g   %s\n",
			      i, top[i], top_names[i]));
	}
}
#else
# define stats_dump()   do { } while (0) /* nothing */
#endif


DEFINEFN
void psyco_stats_append(PyThreadState* tstate, PyFrameObject* f)
{
	double charge;
	float cs_charge;
	int bits;
	time_measure_t numticks;

	if (!measuring_state(tstate))
		return;
	numticks = get_measure(tstate);
	if (measure_is_zero(numticks) || f == NULL)
		return;  /* f==NULL must still make a get_measure() call */
	charge = ((double) charge_unit) * numticks;
	
	bits = c_random();
	while (1) {
		PyCodeStats* cs = PyCodeStats_Get(f->f_code);
		cs_charge = (float)(cs->st_charge + charge);
		cs->st_charge = cs_charge;
		charge_total += charge;
		if (cs_charge > charge_prelimit && charge_callback) {
			/* update charge_prelimit */
			charge_prelimit = (float)(charge_total * charge_watermark);
			if (cs_charge > charge_prelimit) {
				/* still over the up-to-date limit */
				cs->st_charge = 0.0f;
				break;
			}
		}
		if (bits >= 0)
			return;  /* triggers in about 50% of the cases */
		bits <<= 1;
		f = f->f_back;
		if (!f)
			return;
		charge *= charge_parent2;
	}

	/* charge limit reached, invoke callback */
	{
		PyObject* r;
		r = PyObject_CallFunction(charge_callback, "Of", f, cs_charge);
		if (r == NULL) {
			PyErr_WriteUnraisable((PyObject*) f);
		}
		else {
			Py_DECREF(r);
		}
	}
}

DEFINEFN
void psyco_stats_collect(void)
{
	/* collect statistics for all registered threads */
	PyInterpreterState* istate = PyThreadState_Get()->interp;
	PyThreadState* tstate;
	for (tstate=istate->tstate_head; tstate; tstate=tstate->next) {
		psyco_stats_append(tstate, tstate->frame);
	}
}

DEFINEFN
void psyco_stats_reset(void)
{
	/* reset all stats */
	int i = 0;
	PyObject *key, *value, *d;
	stats_printf(("stats: reset\n"));

	/* reset the charge of all PyCodeStats, keep only the used ones */
        RECLIMIT_SAFE_ENTER();
	d = PyDict_New();
	if (d == NULL)
		OUT_OF_MEMORY();
	while (PyDict_Next(codestats_dict, &i, &key, &value)) {
		PyCodeStats* cs = (PyCodeStats*) key;
		if (cs->st_mergepoints) {
			/* clear the charge and keep alive */
			cs->st_charge = 0.0f;
			if (PyDict_SetItem(d, key, value))
				OUT_OF_MEMORY();
		}
	}
        RECLIMIT_SAFE_LEAVE();
	Py_DECREF(codestats_dict);
	codestats_dict = d;
	charge_total = 0.0;
	charge_prelimit = 0.0f;

	/* reset the time measure in all threads */
	{
#if MEASURE_ALL_THREADS
		PyInterpreterState* istate = PyThreadState_Get()->interp;
		PyThreadState* tstate;
		for (tstate=istate->tstate_head; tstate; tstate=tstate->next) {
			(void) get_measure(tstate);
		}
#else
		(void) get_measure(NULL);
#endif
	}
}

DEFINEFN
PyObject* psyco_stats_dump(void)
{
	PyObject* d = PyDict_New();
	int i = 0;
	PyObject *key, *value;
	if (d == NULL)
		return NULL;
	
	while (PyDict_Next(codestats_dict, &i, &key, &value)) {
		PyCodeStats* cs = (PyCodeStats*) key;
		PyObject* o = PyFloat_FromDouble(cs->st_charge);
		extra_assert(PyCStruct_Check(key));
		extra_assert(PyCode_Check(cs->cs_key));
		if (o == NULL || PyDict_SetItem(d, cs->cs_key, o)) {
			Py_DECREF(d);
			return NULL;
		}
	}
	stats_dump();
	return d;
}

DEFINEFN
PyObject* psyco_stats_top(int n)
{
	PyObject* l;
	PyObject* l2 = NULL;
	int i, k=0, full=0;
	PyObject *key, *value;
	float charge_min = (float)(charge_total * 0.001);

	extra_assert(n>0);
	l = PyList_New(n);
	if (l == NULL)
		goto fail;
	
	while (PyDict_Next(codestats_dict, &k, &key, &value)) {
		PyCodeStats* cs = (PyCodeStats*) key;
		extra_assert(PyCStruct_Check(key));
		extra_assert(PyCode_Check(cs->cs_key));
		if (cs->st_charge <= charge_min)
			continue;
		if (full < n)
			full++;
		i = full;
		while (--i > 0) {
			PyObject* o = PyList_GetItem(l, i-1);
			PyCodeStats* current = (PyCodeStats*) o;
			if (cs->st_charge <= current->st_charge)
				break;
                        Py_INCREF(o);
			if (PyList_SetItem(l, i, o))
				goto fail;
		}
		Py_INCREF(cs);
		if (PyList_SetItem(l, i, (PyObject*) cs))
			goto fail;
		cs = (PyCodeStats*) PyList_GetItem(l, full-1);
		charge_min = cs->st_charge;
	}

	l2 = PyList_New(full);
	if (l2 == NULL)
		goto fail;

	for (i=0; i<full; i++) {
		PyCodeStats* cs = (PyCodeStats*) PyList_GetItem(l, i);
                PyObject* x = Py_BuildValue("Od", cs->cs_key,
					(double)(cs->st_charge / charge_total));
		if (!x || PyList_SetItem(l2, i, x))
			goto fail;
	}
	Py_DECREF(l);
	return l2;

 fail:
	Py_XDECREF(l2);
	Py_XDECREF(l);
	return NULL;
}


 /***************************************************************/

#if !MEASURE_ALL_THREADS
DEFINEVAR PyThreadState* psyco_main_threadstate;
#endif


INITIALIZATIONFN
void psyco_stats_init(void)
{
	codestats_dict = PyDict_New();

#if !MEASURE_ALL_THREADS
	psyco_main_threadstate = PyThreadState_Get();
#endif
}
