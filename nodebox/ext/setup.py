from distutils.core import setup, Extension

bezier   = Extension("bezier",   sources=["bezier.c"])
geometry = Extension("geometry", sources=["geometry.c"])
noise    = Extension("noise",    sources=["noise.c"])

setup(
         name = "extensions",
      version = "1.0",
       author = "Tom De Smedt, Frederik De Bleser",
  description = "Fast C Bezier, geometry and noise math.",
  ext_modules = [bezier, geometry, noise]
)