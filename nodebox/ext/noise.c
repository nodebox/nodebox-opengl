// --- PERLIN NOISE --------------------------------------------------------------------
// Based on: Malcolm Kesson, http://www.fundza.com/c4serious/noise/perlin/perlin.html
// © 2002-4 Malcolm Kesson. All rights reserved.

#include <math.h>
#include <stdio.h>

static int p[512];

double fade(double t) { return t * t * t * (t * (t * 6 - 15) + 10); }
double lerp(double t, double a, double b) { return a + t * (b - a); }
double grad(int hash, double x, double y, double z) {
    int     h = hash & 15;
    double  u = h < 8 ? x : y,
            v = h < 4 ? y : h==12 || h==14 ? x : z;
    return ((h&1) == 0 ? u : -u) + ((h&2) == 0 ? v : -v);
}

double _generate(double x, double y, double z) {
    // Find unit cuve that contains point.
    int   X = (int)floor(x) & 255,
          Y = (int)floor(y) & 255,
          Z = (int)floor(z) & 255;
    // Find relative x, y, z of point in cube.
    x -= floor(x);
    y -= floor(y);
    z -= floor(z);
    // Compute fade curves for each of x, y, z.
    double u=fade(x), v=fade(y), w=fade(z);
    // Hash coordinates of the 8 cube corners.
    int  A  = p[X  ] + Y,
         AA = p[A  ] + Z,
         AB = p[A+1] + Z,
         B  = p[X+1] + Y,
         BA = p[B  ] + Z,
         BB = p[B+1] + Z;
    // Add blended results from 8 corners of cube.
    return lerp(w, 
        lerp(v, lerp(u, grad(p[AA  ], x  , y  , z  ), 
                        grad(p[BA  ], x-1, y  , z  )),
                lerp(u, grad(p[AB  ], x  , y-1, z  ), 
                        grad(p[BB  ], x-1, y-1, z  ))),
        lerp(v, lerp(u, grad(p[AA+1], x  , y  , z-1), 
                        grad(p[BA+1], x-1, y  , z-1)),
                lerp(u, grad(p[AB+1], x  , y-1, z-1), 
                        grad(p[BB+1], x-1, y-1, z-1))));
}

// -------------------------------------------------------------------------------------

#include <Python.h> 

static PyObject *
generate(PyObject *self, PyObject *args) {
    double x, y, z, d;   
    if (!PyArg_ParseTuple(args, "ddd", &x, &y, &z)) return NULL;
    d = _generate(x, y, z);
    return Py_BuildValue("d", d);
}

static PyObject *
init(PyObject *self, PyObject *args) {
    PyObject * a;
    if (!PyArg_ParseTuple(args, "O!", &PyList_Type, &a)) return NULL;
    int i;
    for(i=0; i<512; i++)
        p[i] = (int)PyInt_AsLong(PyList_GetItem(a, i));
    return Py_BuildValue("");
}

static PyMethodDef methods[]={ 
    { "generate", generate, METH_VARARGS },
    { "init", init, METH_VARARGS },
    { NULL, NULL }
};

PyMODINIT_FUNC initnoise(void) { 
    PyObject *m;
    m = Py_InitModule("noise", methods);
}

int main(int argc, char *argv[]) {
    Py_SetProgramName(argv[0]);
    Py_Initialize();
    initnoise();
    return 0;
}