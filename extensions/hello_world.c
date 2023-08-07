#include <Python.h>

static PyObject *helloworld(PyObject *self, PyObject *args)
{
    printf("Hello World!\n");
    return Py_None;
}

static PyMethodDef methodList[] = {
    { "helloworld", helloworld, METH_NOARGS, "Prints Hello World" },
    { NULL, NULL, 0, NULL }
};

// Our Module Definition struct
static struct PyModuleDef helloModule = {
    PyModuleDef_HEAD_INIT,
    "helloModule",
    "Test compiled C module",
    -1,
    methodList
};

// Initializes our module using our above struct
PyMODINIT_FUNC PyInit_helloModule(void)
{
    return PyModule_Create(&helloModule);
}
