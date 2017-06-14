from distutils.core import setup, Extension

bezier   = Extension("nglbezier",   sources=["nglbezier.c"])
geometry = Extension("nglgeometry", sources=["nglgeometry.c"])
noise    = Extension("nglnoise",    sources=["nglnoise.c"])

setup(
         name = "Nodebox for OpenGL c-extensions",
      version = "1.0",
       author = "Tom De Smedt, Frederik De Bleser",
  description = "Fast C Bezier, geometry and noise math.",
  ext_modules = [bezier, geometry, noise]
)
