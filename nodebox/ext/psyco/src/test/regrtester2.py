#
# A less memory-exploding version of regrtester.py.
# It runs only a fraction of the tests.
#

import sys, re, psyco


assert len(sys.argv) >= 2
match = re.match(r"(\d+)[/](\d+)", sys.argv[1])
assert match, "syntax: regrtester2.py n/m [-nodump] [seed]"
n = int(match.group(1))
m = int(match.group(2))
assert 0 <= n < m


import test.regrtest
import regrtester

def confirm_still_in_psyco():
    return __in_psyco__

tests = [s for s in test.regrtest.findtests()
         if hash(s) % m == n and s not in test.regrtest.NOTTESTS]
if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == '-nodump':
        dump = 0
        del sys.argv[2]
    else:
        dump = 1
        
    import random, time
    seed = time.ctime()
    if len(sys.argv) > 2:
        seed = sys.argv[2]
        del sys.argv[2]
    print 'Random seed is %r' % seed
    random.seed(seed)
    random.shuffle(tests)

    fully_in_psyco = confirm_still_in_psyco()
    try:
        test.regrtest.main(tests)  #, verbose=1)
    finally:
        if dump:
            psyco.dumpcodebuf()
        if fully_in_psyco:
            assert confirm_still_in_psyco()
