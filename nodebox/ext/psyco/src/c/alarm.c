
/* Define this to compile as a stand-alone "alarm" module */
/*#undef STANDALONE*/

#ifdef STANDALONE
# include <Python.h>
#else
# include "alarm.h"
#endif

/************************************************************/
#ifdef WITH_THREAD
/************************************************************/

#include <pythread.h>


typedef struct {
  PyObject_HEAD
  PyInterpreterState* interp;
  PyThread_type_lock lock;
  PyObject* args;
  enum { st_waiting, st_running, st_stopped } state;
} PyAlarmObject;


staticforward PyTypeObject PyAlarm_Type;

static void t_bootstrap(void* rawself)
{
  PyAlarmObject* self = (PyAlarmObject*) rawself;
  PyThreadState *tstate;
  PyObject* args = NULL;

  tstate = PyThreadState_New(self->interp);
  PyEval_AcquireThread(tstate);

  while (1)
    {
      PyObject *res, *sleepfn, *sleeparg, *callback, *cbarg = NULL;
      Py_XDECREF(args);
      args = self->args;
      Py_XINCREF(args);
      if (args == NULL || args == Py_None)
        break;
      if (!PyArg_ParseTuple(args, "OOO|O", &sleepfn, &sleeparg,
                            &callback, &cbarg))
        break;
      res = PyObject_CallObject(sleepfn, sleeparg);
      if (res == NULL)
        break;
      Py_DECREF(res);
      res = NULL;
      if (self->args == NULL)
        break;

      PyThread_acquire_lock(self->lock, WAIT_LOCK);
      if (self->args != NULL)
        {
          self->state = st_running;
          res = PyObject_CallObject(callback, cbarg);
          self->state = st_waiting;
        }
      PyThread_release_lock(self->lock);
      
      Py_DECREF(args);
      args = self->args;
      self->args = res;
    }
  Py_XDECREF(args);
  Py_XDECREF(self->args);
  self->args = NULL;
  
  self->state = st_stopped;
  if (PyErr_Occurred())
    {
      if (PyErr_ExceptionMatches(PyExc_SystemExit))
        PyErr_Clear();
      else
        {
          PySys_WriteStderr("Unhandled exception in alarm:\n");
          PyErr_PrintEx(0);
        }
    }
  Py_DECREF(self);
  PyThreadState_Clear(tstate);
  PyThreadState_DeleteCurrent();
  PyThread_exit_thread();
}

 /***************************************************************/

static void alarm_dealloc(PyAlarmObject* self)
{
  Py_XDECREF(self->args);
  if (self->lock != NULL)
    PyThread_free_lock(self->lock);
  PyObject_Del((PyObject*) self);
}

#if 0
static int alarm_traverse(PyAlarmObject* self, visitproc visit, void* arg)
{
  if (self->args != NULL)
    return visit(self->args, arg);
  else
    return 0;
}
#endif

PSY_INLINE int alarm_clear(PyAlarmObject* self)
{
  PyObject* nargs = self->args;
  self->args = NULL;
  Py_XDECREF(nargs);
  return 0;
}

static PyObject* alarmstate(PyAlarmObject* self, PyObject* args)
{
  char* s;
  if (!PyArg_ParseTuple(args, ""))
    return NULL;
  switch (self->state) {
  case st_waiting: s = "waiting"; break;
  case st_running: s = "running"; break;
  default:         s = "stopped"; break;
  }
  return PyString_FromString(s);
}

static PyObject* alarmstop(PyAlarmObject* self, PyObject* args)
{
  int wait;
  if (!PyArg_ParseTuple(args, "i", &wait))
    return NULL;
  alarm_clear(self);
  if (wait && self->state != st_stopped)
    {
      Py_BEGIN_ALLOW_THREADS
      PyThread_acquire_lock(self->lock, WAIT_LOCK);
      PyThread_release_lock(self->lock);
      Py_END_ALLOW_THREADS
    }
  Py_INCREF(Py_None);
  return Py_None;
}

#ifdef STANDALONE
static PyObject* new_alarm(PyObject* dummy, PyObject* args)
#else
DEFINEFN
PyObject* psyco_new_alarm(PyObject* dummy, PyObject* args)
#endif
{
  PyAlarmObject* self;
  long ident;

  self = PyObject_New(PyAlarmObject, &PyAlarm_Type);
  if (self == NULL)
    return NULL;
  
  PyEval_InitThreads(); /* Start the interpreter's thread-awareness */
  self->interp = PyThreadState_Get()->interp;
  self->lock = PyThread_allocate_lock();
  Py_INCREF(args);
  self->args = args;
  self->state = st_waiting;

  if (self->lock == NULL) goto error;

  Py_INCREF(self);  /* t_bootstrap consumes a ref */
  ident = PyThread_start_new_thread(t_bootstrap, (void*) self);
  if (ident == -1)
    {
      Py_DECREF(self);
      PyErr_SetString(PyExc_RuntimeError, "can't start new thread");
      goto error;
    }
  return (PyObject*) self;

 error:
  Py_DECREF(self);
  return NULL;
}

 /***************************************************************/

static PyMethodDef alarm_methods[] = {
	{"state",	(PyCFunction)alarmstate,       METH_VARARGS},
	{"stop",	(PyCFunction)alarmstop,        METH_VARARGS},
	{NULL,		NULL}		/* sentinel */
};

static PyObject* alarm_getattr(PyObject* self, char* name)
{
  return Py_FindMethod(alarm_methods, self, name);
}

statichere PyTypeObject PyAlarm_Type = {
	PyObject_HEAD_INIT(NULL)
	0,					/*ob_size*/
	"alarm",				/*tp_name*/
	sizeof(PyAlarmObject),			/*tp_basicsize*/
	0,					/*tp_itemsize*/
	/* methods */
	(destructor)alarm_dealloc,		/*tp_dealloc*/
	0,					/*tp_print*/
	(getattrfunc)alarm_getattr,		/*tp_getattr*/
	0,					/*tp_setattr*/
	0,					/*tp_compare*/
	0,					/*tp_repr*/
	0,					/*tp_as_number*/
	0,					/*tp_as_sequence*/
	0,					/*tp_as_mapping*/
	0,					/*tp_hash*/
	0,					/*tp_call*/
	0,					/* tp_str */
	0,					/* tp_getattro */
	0,					/* tp_setattro */
	0,					/* tp_as_buffer */
	Py_TPFLAGS_DEFAULT,			/* tp_flags */
	0,					/* tp_doc */
	0,					/* tp_traverse */
	0,					/* tp_clear */
};


#ifdef STANDALONE
static PyMethodDef AlarmMethods[] = {
  {"alarm",   new_alarm,   METH_VARARGS},
  {NULL,   NULL}         /* Sentinel */
};

void initalarm()
{
  PyObject* m;
  PyAlarm_Type.ob_type = &PyType_Type;
  m = Py_InitModule("alarm", AlarmMethods);
  if (m == NULL)
    return;
  Py_INCREF(&PyAlarm_Type);
  if (PyModule_AddObject(m, "AlarmType", (PyObject*) &PyAlarm_Type))
    return;
}
#else
INITIALIZATIONFN
void psyco_alarm_init(void)
{
  PyAlarm_Type.ob_type = &PyType_Type;
}
#endif


/************************************************************/
#else   /* if !defined(WITH_THREAD) */
/************************************************************/

#ifdef STANDALONE
# error "Thread support is required for the alarm module"
#else

DEFINEFN
PyObject* psyco_new_alarm(PyObject* dummy, PyObject* args)
{
  PyErr_SetString(PyExc_PsycoError,
                  "Python and Psyco must be compiled with thread support.");
  return NULL;
}

INITIALIZATIONFN
void psyco_alarm_init(void)
{
}
#endif


/************************************************************/
#endif  /* WITH_THREAD */
/************************************************************/
