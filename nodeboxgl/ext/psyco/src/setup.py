#! /usr/bin/env python

"""Psyco shows that it is possible to execute Python code at speeds
approaching that of fully compiled languages, by "specialization".
This extension module for the unmodified interpreter accelerates
user programs with little or not change in their sources, by a
factor that can be very interesting (2-10 times is common)."""

import os, sys
from distutils.core import setup
from distutils.extension import Extension

PROCESSOR = None  # autodetect

####################################################################
#
#  Customizable debugging flags.
#  Copy the following section in a new file 'preferences.py' to
#  avoiding changing setup.py. Uncomment and change the options there
#  at your will. Setting PsycoDebug to 1 is probably the first thing
#  you want to do to enable all internal checks.

#PSYCO_DEBUG = 1

# level of debugging outputs: 0 = none, 1 = a few, 2 = more,
#   3 = detailled, 4 = full execution trace
#VERBOSE_LEVEL = 0

# write produced blocks of code into a file; see 'xam.py'
#  0 = off, 1 = only manually (from a debugger or with _psyco.dumpcodebuf()),
#  2 = only when returning from Psyco,
#  3 = every time a new code block is built
#CODE_DUMP = 1

# Linux-only *heavy* memory checking: 0 = off, 1 = reasonably heavy,
#                                     2 = unreasonably heavy.
#HEAVY_MEM_CHECK = 0

# If the following is set to 1, Psyco is compiled by #including all .c
# files into psyco.c.
# It provides a version of _psyco.so whose only exported (non-static)
# symbol is init_psyco(). It also seems that the GDB debugger doesn't locate
# too well non-static symbols in shared libraries. Recompiling after minor
# changes is faster if ALL_STATIC=0.
ALL_STATIC = 1

# Be careful with ALL_STATIC=0, because I am not sure the distutils can
# correctly detect all the dependencies. In case of doubt always compile
# with `setup.py build_ext -f'.


####################################################################

# override options with the ones from preferences.py, if the file exists.
try:
    execfile('preferences.py')
except IOError:
    pass


# processor auto-detection
class ProcessorAutodetectError(Exception):
    pass
def autodetect():
    platform = sys.platform.lower()
    if platform.startswith('win'):   # assume an Intel Windows
        return 'i386'
    # assume we have 'uname'
    mach = os.popen('uname -m', 'r').read().strip()
    if not mach:
        raise ProcessorAutodetectError, "cannot run 'uname -m'"
    if mach == 'x86_64' and sys.maxint == 2147483647:
        mach = 'x86'     # it's a 64-bit processor but in 32-bits mode, maybe
    try:
        return {'i386': 'i386',
                'i486': 'i386',
                'i586': 'i386',
                'i686': 'i386',
                'i86pc': 'i386',    # Solaris/Intel
                'x86':   'i386',    # Apple
                }[mach]
    except KeyError:
        raise ProcessorAutodetectError, "unsupported processor '%s'" % mach


# loads the list of source files from SOURCEDIR/files.py
# and make the appropriate options for the Extension class.
SOURCEDIR = 'c'

data = {}
execfile(os.path.join(SOURCEDIR, 'files.py'), data)

SRC = data['SRC']
MAINFILE = data['MAINFILE']
PLATFILE = data['PLATFILE']

macros = []
for name in ['PSYCO_DEBUG', 'VERBOSE_LEVEL',
             'CODE_DUMP', 'HEAVY_MEM_CHECK', 'ALL_STATIC',
             'PSYCO_NO_LINKED_LISTS']:
    if globals().has_key(name):
        macros.append((name, str(globals()[name])))

if PROCESSOR is None:
    try:
        PROCESSOR = autodetect()
    except ProcessorAutodetectError:
        PROCESSOR = 'ivm'  # fall back to the generic virtual machine
    print "PROCESSOR = %r" % PROCESSOR
processor_dir = os.path.join('c', PROCESSOR)
localsetup = os.path.join(processor_dir, 'localsetup.py')
if os.path.isfile(localsetup):
    d = globals().copy()
    d['__file__'] = localsetup
    execfile(localsetup, d)

if ALL_STATIC:
    sources = [SOURCEDIR + '/' + MAINFILE,
               SOURCEDIR + '/' + PLATFILE]
else:
    sources = [SOURCEDIR + '/' + s.filename for s in SRC]

extra_compile_args = []
extra_link_args = []
if sys.platform == 'win32':
    if globals().get('PSYCO_DEBUG'):
        # how do we know if distutils will use the MS compilers ???
        # these are just hacks that I really need to compile psyco debug versions
        # on Windows
        extra_compile_args.append('/Od')   # no optimizations, override the default /Ox
        extra_compile_args.append('/ZI')   # debugging info
        extra_link_args.append('/debug')   # debugging info
    macros.insert(0, ('NDEBUG', '1'))  # prevents from being linked against python2x_d.lib


CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: C',
    'Topic :: Software Development :: Compilers',
    'Topic :: Software Development :: Interpreters',
    ]

try:
    import distutils.command.register
except ImportError:
    kwds = {}
else:
    kwds = {'classifiers': CLASSIFIERS}

py_modules = ['psyco.%s' % os.path.splitext(fn)[0]
              for fn in os.listdir('py-support')
              if os.path.splitext(fn)[1].lower() == '.py']
py_modules.remove('psyco.__init__')

if sys.version_info < (2, 2, 2):
    raise Exception("Psyco >= 1.5.3 requires Python >= 2.2.2")


setup (	name             = "psyco",
      	version          = "1.5.2",
      	description      = "Psyco, the Python specializing compiler",
      	author           = "Armin Rigo",
        author_email     = "arigo@users.sourceforge.net",
      	url              = "http://psyco.sourceforge.net/",
        license          = "MIT License",
        long_description = __doc__,
        platforms        = ["i386"],
        py_modules       = py_modules,
        package_dir      = {'psyco': 'py-support'},
      	ext_modules=[Extension(name = 'psyco._psyco',
                               sources = sources,
                               extra_compile_args = extra_compile_args,
                               extra_link_args = extra_link_args,
                               define_macros = macros,
                               include_dirs = [processor_dir])],
        **kwds )
