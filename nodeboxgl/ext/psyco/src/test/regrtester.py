import sys, os, test.regrtest

import psyco
import time; print "Break!"; time.sleep(0.5)
psyco.log()
if os.path.exists('regrtester.local'):
    execfile('regrtester.local')
else:
    psyco.full()


#################################################################################
SKIP = {'test_gc': "test_gc.test_frame() does not create a cycle with Psyco's limited frames",
        'test_descr': 'seems that it mutates user-defined types and Psyco does not like it at all',
        'test_profilehooks': 'no profiling allowed with Psyco!',
        'test_profile': 'no profiling allowed with Psyco!',
        'test_cProfile': 'no profiling allowed with Psyco!',
        'test_repr': 'self-nested tuples and lists not supported',
        'test_trace': 'no line tracing with Psyco',
        'test_threaded_import': 'Python hang-ups',
        'test_hotshot': "PyEval_SetProfile(NULL,NULL) doesn't allow Psyco to take control back",
        'test_richcmp': 'uses eval() with locals and circular data structure cmps',
        'test_longexp': 'run it separately if you want, but it takes time and memory',
        'test_weakref': 'only run with FULL_CONTROL_FLOW set to 0 in mergepoints.c',
        'test_gettext': 'gettext mutates _ in the builtins!',
        'test_inspect': 'isframe() does not recognize our Frame instances',
        'test_exceptions': 'uses tb.tb_frame.f_back',
        'test_largefile': 'fails on Python on my old Linux box',
        'test_popen2': 'log file descriptor messed up in Python < 2.2.2',
        'test_sys': 'getrefcount() cannot be reliably tested',
        'test_socket': 'refcounting stuff as well',
        #'test_copy': 'xrange() is very similar to range() with Psyco',
        'test_tarfile': 'we get permission denied with Python',
        'test_scope': 'refcounting: relies on the __del__ of instances',
        'test_sax': 'fails without Psyco due to my Expat installation',
        'test_email': 'broken? on \n vs. \r\n',
        'test_mmap': '"invalid handle" with Python 2.2.2',
        'test_winsound': 'winsound fails on Python 2.3 on my machine',
        'test_strptime': "fails about my timezone ending in (heure d'ete) in 2.3",
        'test_atexit': "windows: tired to work around w9xpopen magic",
        'test_popen': "windows: tired to work around w9xpopen magic",
        'test_mimetypes': 'fail in 2.3 if run after test_urllib',
        'test_doctest': 'doctest uses the debugger!?',
        'test_subprocess': 'suspect subprocess messes up stdout with Psyco messages',
        'test_linuxaudiodev': 'this /dev is absent or unreliable on a few machines of mine',
        'test_tcl': 'requires $DISPLAY',
        'test_pep352': 'no warning for string exceptions',
        'test_ctypes': 'it is full of sys.getrefcount() assertions',
        'test_import': 'I hack my pythons to not import bare .pyc files any more',
        'test_runpy':  'I hack my pythons to not import bare .pyc files any more',
        'test_genexps': 'doctests checking the exact error message',
	}
#    SKIP['test_operator'] = NO_SYS_EXC
#    SKIP['test_strop'] = NO_SYS_EXC
#if sys.version_info[:2] >= (2,3):
#    SKIP['test_threadedtempfile'] = 'Python bug: Python test just hangs up'

if sys.version_info[:3] == (2,4,0):
    SKIP['test_distutils'] = 'distutils/tests/* not copied by the installer'

if hasattr(psyco._psyco, 'VERBOSE_LEVEL'):
    SKIP['test_popen2'] = 'gets confused by Psyco debugging output to stderr'

if os.path.exists('regrtester.skip'):
    execfile('regrtester.skip')

#################################################################################


# the tests that don't work with Psyco
test.regrtest.NOTTESTS += SKIP.keys()
if __name__ == '__main__':
    try:
        test.regrtest.main(randomize=1)
    finally:
        psyco.dumpcodebuf()
