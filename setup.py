import os
from setuptools import setup, find_packages


# Utility function to read the README file.
# From http://packages.python.org/an_example_pypi_project/setuptools.html.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name="nodebox-opengl",
    version="1.6.1",
    description="NodeBox for OpenGL is a free, cross-platform library for "
                "generating 2D animations with Python programming code.",
    long_description=read("README.txt"),
    keywords="2d graphics sound physics games multimedia",
    license="BSD",
    author="Tom De Smedt, Frederik De Bleser",
    url="http://www.cityinabottle.org/nodebox/",
    packages=find_packages(),
    package_data={
        "nodebox.gui": ["theme/*"]
    },
    install_requires=[
        "pyglet",
    ],
    classifiers=[
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
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
