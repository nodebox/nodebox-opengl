from distutils.core import setup, Extension

bezier   = Extension("nglbezier",   sources=["bezier.c"])
geometry = Extension("nglgeometry", sources=["geometry.c"])
noise    = Extension("nglnoise",    sources=["noise.c"])

setup(
         name = "Nodebox for OpenGL c-extensions",
      version = "1.0",
       author = "Tom De Smedt, Frederik De Bleser",
  description = "Fast C Bezier, geometry and noise math.",
  ext_modules = [bezier, geometry, noise]
)
