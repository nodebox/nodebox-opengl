#include <Python.h>

static PyObject* any_pointer(PyObject* self, PyObject* args)
{
  char* from;
  int fromlen, i;
  long addr0, start, end, intervallen;
  if (!PyArg_ParseTuple(args, "ls#ll", &addr0, &from, &fromlen, &start, &end))
    return NULL;

  intervallen = end-start;
  for (i=0; i<=fromlen-4; i++)
    {
      long offset = *(long*) (from+i);
      offset -= start;
      if (((unsigned long)(addr0+i+offset)) < intervallen ||
          ((unsigned long) offset) < intervallen)
        return PyInt_FromLong(1);
    }
  return PyInt_FromLong(0);
}

static PyMethodDef XamMethods[] = {
  {"any_pointer", any_pointer, METH_VARARGS},
  {NULL,   NULL}         /* Sentinel */
};

void initxamsupport()
{
  Py_InitModule("xamsupport", XamMethods);
}
