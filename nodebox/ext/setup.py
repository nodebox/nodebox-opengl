from distutils.core import setup, Extension

bezier_math   = Extension("bezier_math", sources=["bezier_math.c"])
geometry_math = Extension("geometry_math", sources=["geometry_math.c"])

setup(
       name = "extensions",
    version = "1.0",
     author = "Tom De Smedt, Frederik De Bleser",
    description = "Fast C Bezier and geometry math.",
    ext_modules = [bezier_math, geometry_math]
)