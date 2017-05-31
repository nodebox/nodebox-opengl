import os
from setuptools import setup
from setuptools import find_packages

# Utility function to read the README file.
# From http://packages.python.org/an_example_pypi_project/setuptools.html.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(      name = "NodeBox for OpenGL",
         version = "1.7",
     description = "NodeBox for OpenGL (NOGL) is a free, cross-platform library "
                   "for generating 2D animations with Python programming code.",
long_description = read("README.txt"),
        keywords = "2d graphics sound physics games multimedia",
         license = "BSD",
          author = "Tom De Smedt",
             url = "http://www.cityinabottle.org/nodebox/",
        packages = find_packages(),
    package_data = {"nodeboxgl.gui": ["theme/*"], "nodeboxgl.font":["glyph.p"]},
install_requires = ["pyglet",],
      py_modules = ["nodeboxgl", "nodeboxgl.graphics", "nodeboxgl.gui", "nodeboxgl.sound", "nodeboxgl.font"],
     classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Topic :: Artistic Software",
        "Topic :: Games/Entertainment",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Scientific/Engineering :: Visualization",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
