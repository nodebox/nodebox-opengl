import sys, os, StringIO, psyco, psyco.logger

LOGFILE = 'log-regrtest-psyco'


#NO_SYS_GETFRAME = """using sys._getframe() fails with Psyco"""

#NO_THREAD = """XXX not reliable, check if Psyco is generally
#        unreliable with threads or if there is another problem"""

#NO_PICKLE = """pickles function objects that Psyco rebinds"""

#NO_SYS_EXC = """XXX Psyco does not set sys.exc_xxx upon exception"""


SKIP = {'test_gc': "test_gc.test_frame() does not create a cycle with Psyco's limited frames",
#        'test_thread': NO_THREAD,
#        'test_asynchat': NO_THREAD,
#        'test_extcall': 'prints to stdout a function object that Psyco rebinds',
        'test_descr': 'seems that it mutates user-defined types and Psyco does not like it at all',
#        'test_pickle': NO_PICKLE,
#        'test_cpickle': NO_PICKLE,
#        'test_re': NO_PICKLE,
#        'test_sre': NO_SYS_EXC,
#        'test_string': NO_SYS_EXC,
#        'test_unicode': NO_SYS_EXC,
#        'test_inspect': 'gets confused with Psyco rebinding functions',
        'test_profilehooks': 'profiling does not see all functions run by Psyco',
        'test_profile': 'profiling does not see all functions run by Psyco',
        'test_repr': 'self-nested tuples and lists not supported',
        'test_builtin': 'vars() and locals() not supported',
        'test_inspect': 'does not run even in Python (when called the way classicregrtest.py calls it) and leaves buggy temp files around',
        'test_trace': 'no line tracing with Psyco',
        'test_threaded_import': 'Python hang-ups',
        'test_hotshot': "PyEval_SetProfile(NULL,NULL) doesn't allow Psyco to take control back",
        'test_coercion': 'uses eval() with locals',
        'test_weakref': 'incompatible with early unused variable deletion',
        }
#    SKIP['test_operator'] = NO_SYS_EXC
#    SKIP['test_strop'] = NO_SYS_EXC
if sys.version_info[:2] >= (2,3):
    SKIP['test_threadedtempfile'] = 'Python bug: Python test just hangs up'

if hasattr(psyco._psyco, 'VERBOSE_LEVEL'):
    SKIP['test_popen2'] = 'gets confused by Psyco debugging output to stderr'

GROUP_TESTS = 5    # number of tests to run per Python process


if '' in sys.path:
    sys.path.remove('')  # don't import the test.py in this directory!

from test import regrtest, test_support

repeat_counter = 4


def alltests():
    import random
    # randomize the list of tests, but try to ensure that we start with
    # not-already-seen tests and only after go on with the rest
    try:
        os.unlink(LOGFILE)
    except OSError:
        pass
    filename = "tmp_tests_passed"
    try:
        f = open(filename)
        tests_passed = eval(f.read())
        f.close()
    except IOError:
        tests_passed = {}
    testlist = regrtest.findtests()
    testlist = [test for test in testlist if not tests_passed.has_key(test)]
    random.shuffle(testlist)
    testlist1 = tests_passed.keys()
    random.shuffle(testlist1)
    print '\t'.join(['Scheduled tests:']+testlist)
    if testlist1:
        print '%d more tests were already passed and are scheduled to run thereafter.' % len(testlist1)
    testlist += testlist1
    while testlist:
        print '='*40
        tests1 = testlist[:GROUP_TESTS]
        del testlist[:GROUP_TESTS]
        err = os.system('"%s" %s %s' % (sys.executable, sys.argv[0],
                                          ' '.join(tests1)))
        if err:
            print '*** exited with error code', err
            return err
        for test in tests1:
            tests_passed[test] = 1
        f = open(filename, 'w')
        f.write(repr(tests_passed))
        f.close()
    print "="*60
    print
    print "Classic Regression Tests with Psyco successfully completed."
    print "All tests that succeeded twice in the same Python process"
    print "also succeeded %d more times with Psyco activated." % repeat_counter
    print
    try:
        os.unlink(filename)
    except:
        pass
    print "Psyco compilation flags:",
    d = psyco._psyco.__dict__
    if not d.has_key('ALL_CHECKS'):
        print "Release mode",
    for key in d.keys():
        if key == key.upper() and type(d[key]) == type(0):
            print "%s=%s" % (key, hex(d[key])),
    print

def python_check(test):
    if SKIP.has_key(test):
        print '%s skipped -- %s' % (test, SKIP[test])
        return 0
    for i in range(min(repeat_counter, 2)):
        print '%s, Python iteration %d' % (test, i+1)
        ok = regrtest.runtest(test, 0, 0, 0)
        special_cleanup()
        if ok <= 0:
            return 0   # skipped or failed -- don't test with Psyco
    return 1

def main(testlist, verbose=0, use_resources=None):
    if use_resources is None:
        use_resources = []
    test_support.verbose = verbose      # Tell tests to be moderately quiet
    test_support.use_resources = use_resources
    
    if type(testlist) == type(""):
        testlist = [testlist]
    if not verbose:
        testlist = filter(python_check, testlist)

    # Psyco selective compilation is only activated here
    psyco.log(LOGFILE, 'a')
    for test in testlist:
        psyco.logger.write('with test ' + test, 1)
    psyco.full()
    #print "sleeping, time for a Ctrl-C !..."
    #import time; time.sleep(1.5)


    for test in testlist:
        for i in range(repeat_counter):
            print '%s, Psyco iteration %d' % (test, i+1)
            ok = regrtest.runtest(test, 0, verbose, 0)
            special_cleanup()
            if ok == 0:
                return 0
            elif ok < 0:
                break
    return 1

def special_cleanup():
    try:
        dircache = sys.modules['dircache']
    except KeyError:
        pass
    else:
        for key in dircache.cache.keys():
            del dircache.cache[key]


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        sys.exit(alltests() or 0)
    else:
        try:
            err = not main(sys.argv[1:])
        finally:
            # Write psyco.dump
            psyco.dumpcodebuf()
        if err:
            sys.exit(2)
