from distutils.core import setup, Extension

bezier_math = Extension("bezier_math", sources = ["bezier_math.c"])

setup (name = "bezier_math",
       version = "1.0",
       author = "Tom De Smedt and Frederik De Bleser",
       description = "Inner looping functions for calculating bezier operations.",
       ext_modules = [bezier_math])