#include <Python.h>
#include <math.h>

// --- FAST INVERSE SQRT --------------------------------------------------------
// Chris Lomont, http://www.math.purdue.edu/~clomont/Math/Papers/2003/InvSqrt.pdf
float _fast_inverse_sqrt(float x) {
    float xhalf = 0.5f*x;
    int i = *(int*)&x;
    i = 0x5f3759df - (i>>1);
    x = *(float*)&i;
    x = x*(1.5f-xhalf*x*x);
    return x;
}

// --- ANGLE --------------------------------------------------------------------
void _angle(double x0, double y0, double x1, double y1, double *a) {
    *a = atan2(y1-y0, x1-x0) / M_PI * 180;
}

// --- DISTANCE -----------------------------------------------------------------
void _distance(double x0, double y0, double x1, double y1, double *d) {
    *d = 1.0 / _fast_inverse_sqrt((x1-x0)*(x1-x0) + (y1-y0)*(y1-y0));
}

// --- COORDINATES --------------------------------------------------------------
void _coordinates(double x0, double y0, double d, double a, double *x1, double *y1) {
    *x1 = x0 + cos(a/180*M_PI) * d;
    *y1 = y0 + sin(a/180*M_PI) * d;
}

// --- ROTATE -------------------------------------------------------------------
void _rotate(double x, double y, double x0, double y0, double a, double *x1, double *y1) {
    x = x-x0;
    y = y-y0;
    double u = cos(a/180*M_PI);
    double v = sin(a/180*M_PI);
    *x1 = x*u-y*v+x0;
    *y1 = y*u+x*v+y0;
}

// --- REFLECT ------------------------------------------------------------------
void _reflect(double x0, double y0, double x1, double y1, double d, double a, double *x, double *y) {
    double d1;
    double a1;
    _distance(x0, y0, x1, y1, &d1);
    _angle(x0, y0, x1, y1, &a1);
    _coordinates(x0, y0, d*d1, a+a1, &*x, &*y);
}

// ------------------------------------------------------------------------------

static PyObject *
fast_inverse_sqrt(PyObject *self, PyObject *args) {
    double x;   
    if (!PyArg_ParseTuple(args, "d", &x))
        return NULL;
    x = _fast_inverse_sqrt(x);
    return Py_BuildValue("d", x);
}

static PyObject *
angle(PyObject *self, PyObject *args) {
    double x0, y0, x1, y1, a;   
    if (!PyArg_ParseTuple(args, "dddd", &x0, &y0, &x1, &y1))
        return NULL;
    _angle(x0, y0, x1, y1, &a);
    return Py_BuildValue("d", a);
}

static PyObject *
distance(PyObject *self, PyObject *args) {
    double x0, y0, x1, y1, d;   
    if (!PyArg_ParseTuple(args, "dddd", &x0, &y0, &x1, &y1))
        return NULL;
    _distance(x0, y0, x1, y1, &d);
    return Py_BuildValue("d", d);
}

static PyObject *
coordinates(PyObject *self, PyObject *args) {
    double x0, y0, d, a, x1, y1;   
    if (!PyArg_ParseTuple(args, "dddd", &x0, &y0, &d, &a))
        return NULL;
    _coordinates(x0, y0, d, a, &x1, &y1);
    return Py_BuildValue("dd", x1, y1);
}

static PyObject *
rotate(PyObject *self, PyObject *args) {
    double x, y, x0, y0, a, x1, y1;   
    if (!PyArg_ParseTuple(args, "ddddd", &x, &y, &x0, &y0, &a))
        return NULL;
    _rotate(x, y, x0, y0, a, &x1, &y1);
    return Py_BuildValue("dd", x1, y1);
}

static PyObject *
reflect(PyObject *self, PyObject *args) {
    double x0, y0, x1, y1, d, a, x, y;   
    if (!PyArg_ParseTuple(args, "dddddd", &x0, &y0, &x1, &y1, &d, &a))
        return NULL;
    _reflect(x0, y0, x1, y1, d, a, &x, &y);
    return Py_BuildValue("dd", x, y);
}

// ------------------------------------------------------------------------------

static PyMethodDef geometry_methods[]={
    { "fast_inverse_sqrt", fast_inverse_sqrt, METH_VARARGS },
    { "angle", angle, METH_VARARGS },
    { "distance", distance, METH_VARARGS },
    { "coordinates", coordinates, METH_VARARGS }, 
    { "rotate", rotate, METH_VARARGS },
    { "reflect", reflect, METH_VARARGS }, 
    { NULL, NULL }
};

PyMODINIT_FUNC initgeometry_math(void){
    PyObject *m;
    m = Py_InitModule("geometry_math", geometry_methods);
}

int main(int argc, char *argv[]) {
    Py_SetProgramName(argv[0]);
    Py_Initialize();
    initgeometry_math();
    return 0;
}