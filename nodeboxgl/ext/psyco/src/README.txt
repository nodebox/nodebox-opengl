======================================================================
               Psyco, the Python Specializing Compiler
======================================================================


                             VERSION 1.5.2+SVN
                             -----------------

Psyco is a Python extension module which can massively speed up the
execution of any Python code.


REQUIREMENTS
------------

Psyco works on almost any version of Python (currently 2.2.2
to 2.5).  At present it *requires* a *32-bit* *PC* (i.e. a
386-compatible processor), but it is OS-independant.

This program is still and will always be incomplete, but it
has been stable for a long time and can give good results.

There are no plans to port Psyco to 64-bit architectures.
This would be rather involved.  Psyco is only being
maintained, not further developed.  The development efforts of
the author are now focused on PyPy, which will include
Psyco-like techniques.  (http://codespeak.net/pypy)

Psyco requires Python >= 2.2.2.  Support for older versions
has been dropped after Psyco 1.5.2.


QUICK INTRODUCTION
------------------

To install Psyco, do the usual

   python setup.py install

Manually, you can also put the 'psyco' package in your Python search
path, e.g. by copying the subdirectory 'psyco' into the directory
'/usr/lib/python2.x/site-packages' (default path on Linux).

Basic usage is very simple: add

  import psyco
  psyco.full()

to the beginning of your main script. For basic introduction see:

  import psyco
  help(psyco)


DOCUMENTATION AND LATEST VERSIONS
---------------------------------

Home page:

  *  http://psyco.sourceforge.net

The current up-to-date documentation is the Ultimate Psyco Guide.
If it was not included in this distribution ("psycoguide.ps" or
"psycoguide/index.html"), see the doc page:

  *  http://psyco.sourceforge.net/doc.html


DEBUG BUILD
-----------

To build a version of Psyco that includes debugging checks and/or
debugging output, see comments in setup.py.


----------
Armin Rigo.
