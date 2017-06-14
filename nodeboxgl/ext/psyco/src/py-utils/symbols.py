import sys, os
import xam

"""
This script loads a psyco.dump file (like httpxam.py) and
reads on its standard input a list of addresses. For each
address that it recognizes it prints the name of the
corresponding symbol or the address of the code buffer
that contains the address. Use this on debugger memory
dumps.

This could be enhanced by detecting the addresses of
vinfo_t's as well.
"""


def main(codebufs, f):
    while 1:
        line = f.readline()
        if not line:
            break
        for addr in xam.lineaddresses(line):
            sym = xam.symbols.get(addr)
            if sym:
                print '0x%x\tis\t' % addr, xam.symtext(sym, addr)
                break


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print "Usage: python symbols.py <directory>"
        print "  psyco.dump is loaded from the <directory>."
        sys.exit(1)
    DIRECTORY = sys.argv[1]
    del sys.argv[1]
    codebufs = xam.readdump(os.path.join(DIRECTORY, 'psyco.dump'))
    print >> sys.stderr, "Reading for addresses from stdin..."
    main(codebufs, sys.stdin)
