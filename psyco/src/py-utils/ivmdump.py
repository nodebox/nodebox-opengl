import sys, os
from struct import unpack, calcsize, error


class argtypes:
    char = "b", "0x%x"
    byte = code_t = "B", "0x%x"
    int  = "i", "0x%x"
    long = word_t = "l", "0x%x"
    def stack(t):
        if isinstance(t, tuple):
            return t[0], "[%d]"
        else:
            return "", "[%s]" % t, t
    def indirect(t):
        return t

fn = os.path.join(os.path.dirname(__file__), '../c/ivm/prolog/insns-table.py')
execfile(fn, argtypes.__dict__, globals())


class Mode:
    
    def __init__(self, opcode):
        self.opcode = opcode
        if opcode in insntable:
            self.insns = insntable[opcode]
        else:
            self.insns = [("<%d>" % opcode,)]
        if len(self.insns) == 1:
            self.singleinsn = self.insns[0][0]
        else:
            self.singleinsn = None
        self.stackpushes = stackpushes.get(opcode)
        self.unpackfmt = "="
        self.template = ""
        self.constantargs = []
        i = 0
        line = '%10x\t'
        for insn in self.insns:
            args = []
            for arg in insn[1:]:
                if isinstance(arg, tuple):
                    self.unpackfmt += arg[0]
                    args.append(arg[1])
                    if len(arg)>2:
                        self.constantargs.append((i, arg[2]))
                else:
                    args.append(str(arg))
                    self.constantargs.append((i, arg))
                i += 1
            line += '%-11s %s' % (insn[0], ', '.join(args))
            self.template += line
            line = '\n          \t'
        self.unpacksize = calcsize(self.unpackfmt)
        
    def dump(self, data, address, position):
        data = data[position:position+self.unpacksize]
        args = unpack(self.unpackfmt, data)
        result = self.template % ((address,) + args)
        return position+self.unpacksize, result.split('\n'), args

    def getargs(self, data, position):
        data = data[position:position+self.unpacksize]
        args = list(unpack(self.unpackfmt, data))
        for i, value in self.constantargs:
            args.insert(i, value)
        return args

insnlist = [Mode(opcode) for opcode in range(256)]


def dump(data, originaddr):
    l = len(data)
    if l>8 and data[-4:] == '\x00\x00\x00\x00':
        p, = unpack("l", data[-8:-4])
        queue = ["", "          (promotion chained list: 0x%x)" % p]
        l -= 4
    else:
        queue = []
    depth = None
    result = []
    p = 0
    try:
        while p < l:
            mode = insnlist[ord(data[p])]
            p, lines, args = mode.dump(data, originaddr+p, p+1)
            if depth is not None:
                if mode.stackpushes is None:
                    depth = None
                else:
                    depth += mode.stackpushes
                    lines[-1] = '%-40s [%d]' % (lines[-1], depth)
            if mode.singleinsn == 'assertdepth':
                asserteddepth = args[0]/4
                if depth is not None and asserteddepth != depth:
                    err = '************* assertion error **************'
                    lines.append(err)
                    print >> sys.stderr, err
                    print >> sys.stderr, originaddr
                else:
                    lines = [(s+' ')[:s.find('assertdepth')] for s in lines]
                depth = asserteddepth
            result += lines
    except error:
        while p < l:
            result.append("  %10x\t<%d>" % (originaddr+p, ord(data[p])))
            p += 1
    result += queue
    return result
