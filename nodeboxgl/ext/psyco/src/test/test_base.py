#! /usr/bin/env python

"""  Run base Psyco tests.
"""

import sys, os, random, doctest, cStringIO
True,False = 1==1,1==0


SEPARATOR = """
========== %r ==========
"""
LASTLINE = "Tests completed."
BUFFERFILE = "buffer-basetests.txt"
EXPECTEDFILE = "expected-basetests.txt"
INPUTSCRIPT = "input-basetexts.py"

TESTS = open('btrun.py', 'r').read()


if hasattr(doctest, '_extract_examples'):
    tests = doctest._extract_examples(TESTS)
else:
    examples = doctest.DocTestParser().get_examples(TESTS)
    tests = [(example.source, example.want, example.lineno)
             for example in examples]

# ---

def main(quiet=False):
    PRELUDE = ''
    for inp, outp, line in tests[:]:
        if not outp:
            PRELUDE += inp + '\n'
            tests.remove((inp, outp, line))
    random.shuffle(tests)             # first run all tests in any order
    tests_again = tests[:]
    random.shuffle(tests_again)
    all_tests = tests + tests_again   # then run them all again in any other order

    childin = open(INPUTSCRIPT, 'w')
    expected = open(EXPECTEDFILE, 'w')

    print >> childin, 'import sys'
    print >> childin, PRELUDE

    def filterline(line):
        if line.startswith('${') and line.endswith('}'):
            line = str(eval(line[2:-1]))
        return line

    for inp, outp, line in all_tests:
        sep = SEPARATOR % inp
        print >> childin, 'print %r' % sep
        if not quiet:
            print >> childin, 'print >> sys.stderr, %r' % inp.strip()
        print >> expected, sep
        print >> childin, inp
        outplines = [filterline(line) for line in outp.split('\n')]
        expected.write('\n'.join(outplines))

    print >> childin, 'print %r' % LASTLINE
    print >> expected, LASTLINE
    expected.close()
    childin.close()

    # run in a child process
    err = os.system('"%s" %s > %s' % (sys.executable, INPUTSCRIPT, BUFFERFILE))
    print >> sys.stderr
    if err:
        print >> sys.stderr, 'FAIL: child process returned %d, %d' % (err>>8, err&255)
        sys.exit(1)
    else:
        data1 = open(EXPECTEDFILE, 'r').read()
        data2 = open(BUFFERFILE, 'r').read()
        if data1 != data2:
            print >> sys.stderr, 'FAIL: different output'
            if sys.argv[1:2] != ['-q']:
                cmd = 'diff -c %s %s' % (EXPECTEDFILE, BUFFERFILE)
                os.system(cmd)
            return False
        else:
            print >> sys.stderr, 'Passed.'
            return True

def test_main():
    ok = main(quiet=True)
    assert ok

if __name__ == '__main__':
    if not main():
        sys.exit(1)
