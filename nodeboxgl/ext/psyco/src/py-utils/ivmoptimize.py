"""
python ivmoptimize.py path [ path ... ]

This script optimizes and regenerates the 'ivm' virtual machine
used by Psyco on non-i386 platforms.  You need to compile Psyco
in debugging mode (see below) and use 'psyco.dumpcodebuf()' to
generate one or more dump files called 'psyco.dump'.  Run then
the present script with the path(s) to the 'psyco.dump' file(s).
Finally, you have to recompile Psyco in normal (optimized) mode.

You need SWI Prolog to do that.  http://www.swi-prolog.org/

To compile Psyco in debugging mode, create a file 'preferences.py'
in the same directory as 'setup.py' with the following content:

PROCESSOR = 'ivm'
PSYCO_DEBUG = 1
VERBOSE_LEVEL = 1
CODE_DUMP = 1

and re-run 'python setup.py build -f install'.
"""
import sys, os
import ivmextract

try:
    LOCALDIR = __file__
except NameError:
    LOCALDIR = sys.argv[0]
LOCALDIR = os.path.dirname(LOCALDIR)


def main(paths, maxlength=8, optmode='optimize.pl'):
    outfilenames = [os.path.abspath(ivmextract.main(dir)) for dir in paths]
    os.chdir(os.path.join(LOCALDIR, os.pardir, 'c', 'ivm', 'prolog'))
    g = open("mode_combine.pl", "w")
    g.close()      # empty file
    g = os.popen('pl -f %s -g remotecontrol -t halt' % optmode, 'w')
    for fn in outfilenames:
        print >> g, "loaddumpfile('%s')." % fn
    print >> g, "measure(%d)." % maxlength
    print >> g, "emitmodes(255)."
    g.close()
    g = open("mode_combine.pl", "r")
    if not g.readline():
        print >> sys.stderr, "*** the Prolog program %s failed" % optmode
        sys.exit(1)
    g.close()
    err = os.system('pl -f insns.pl -g main_emit -t halt')
    if err == 0:
        print
        print 'Done.  If you compile Psyco, its ivm virtual machine will now'
        print 'be optimized for the usage patterns found in the dump files.'


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print >> sys.stderr, __doc__
        sys.exit(2)
    else:
        main(sys.argv[1:])
