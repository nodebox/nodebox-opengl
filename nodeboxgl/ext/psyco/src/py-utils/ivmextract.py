import os, sys
import xam
from ivmdump import insnlist, insntable, stackpushes, chainable
from struct import unpack


IGNORE_INSNS = ('assertdepth', 'dynamicfreq')

def dump(data):
    l = len(data)
    p = 0
    results = []
    result = []
    freq = 1
    while p < l:
        mode = insnlist[ord(data[p])]
        if mode.opcode not in insntable:
            break
        p += mode.unpacksize + 1
        if p > l:
            break
        args = mode.getargs(data, p-mode.unpacksize)
        for insn in mode.insns:
            if insn[0] in IGNORE_INSNS:
                if insn[0] == 'dynamicfreq':
                    freq = args[0]
                continue
            a = len(insn)-1
            if a:
                txt = '%s(%s)' % (insn[0], ','.join(map(str,args[:a])))
                del args[:a]
            else:
                txt = insn[0]
            result.append(txt)
        if mode.opcode not in chainable:
            results.append((freq, result))
            result = []
    results.append((freq, result))
    return results


def main(DIRECTORY):
    filename = os.path.join(DIRECTORY, 'psyco.dump')
    if not os.path.isfile(filename) and os.path.isfile(DIRECTORY):
        filename = DIRECTORY
        DIRECTORY = os.path.dirname(DIRECTORY)
    outfilename = filename + '.ivm'
    if os.path.isfile(filename):
        codebufs = xam.readdump(filename)
        f = open(outfilename, 'w')
        for codebuf in codebufs:
            if codebuf.data:
                data, addr, next, key = codebuf.splitheader()
                for freq, lst in dump(data):
                    if len(lst) > 1:
                        print >> f, 'psycodump(%d, [%s]).' % (freq,
                                                              ', '.join(lst))
        f.close()
    elif not os.path.isfile(outfilename):
        print >> sys.stderr, filename, "not found."
        sys.exit(1)
    else:
        print >> sys.stderr, "reusing text dump from", outfilename
    return outfilename


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print "Usage: python ivmextract.py <directory>"
        print "  psyco.dump is loaded from the <directory>."
        sys.exit(2)
    for dir in sys.argv[1:]:
        print "'%s'." % main(dir)
