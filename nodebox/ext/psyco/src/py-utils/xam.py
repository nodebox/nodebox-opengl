from __future__ import nested_scopes
import os, sys, re, htmlentitydefs, struct, bisect
__metaclass__ = type

tmpfile = '~tmpfile.tmp'

# the disassembler to use. 'objdump' writes GNU-style instructions.
# 'ndisasm' uses Intel syntax.

objdump = 'objdump -b binary -m i386 --adjust-vma=%(origin)d -D %(file)s'
if sys.platform == "win32":
    try:
        from xam import __file__ as _xamfile
    except ImportError:
        raise ImportError, "could not import xam module"
    _win32_path = os.path.join(os.path.split(_xamfile)[0], "win32")
    objdump = os.path.join(_win32_path, objdump)
    _objdumpexe = objdump.split()[0]+".exe"
    # test whether it works:
    if os.system(_objdumpexe + " -v"):
        raise IOError, "file %s and cygwin1.dll must exist" % _objdumpexe
#objdump = 'ndisasm -o %(origin)d -u %(file)s'

# the files from which symbols are loaded.
# the order and number of files must match
# psyco_dump_code_buffers() in psyco.c.
symbolfiles = [sys.executable]
try:
    from psyco import _psyco
    symbolfiles.append(_psyco.__file__)
except ImportError:
    pass

# the program that lists symbols, and the output it gives
symbollister = 'nm %s'
re_symbolentry = re.compile(r'([0-9a-fA-F]+)\s\w\s(.*)')

if sys.platform == "win32":
    # no way to get full info into the executables by
    # VC7. /PDB:NONE no longer supported.
    # so we have to read the map files.
    if sys.executable.lower().endswith("_d.exe"):
        _mapfiles = ("python23_d.map", "_psyco_d.map")
    else:
        _mapfiles = ("python23.map", "_psyco.map")
    symbolfiles = [os.path.join(_win32_path, x) for x in _mapfiles]
    for _filepath in symbolfiles:
        if not os.path.exists(_filepath):
            raise IOError, "please make sure that '%s' exists" % _filepath
        
    class symbollister:
        def __init__(self, filename):
            self.file = file(filename)
            self.generator = self._readline()

        def _readline(self):
            for line in self.file:
                #  0001:000661e0       _PyEval_CallFunction       1e0671e0 f   modsupport.obj
                #  0003:0000e770       _PyClass_Type              1e0d8770     classobject.obj
                pieces = line.split()
                if len(pieces) == 5:
                    colonadr, name, adr, dummy, obj = pieces
                elif len(pieces) == 4:
                    colonadr, name, adr, obj = pieces
                    dummy = "d"
                else:
                    continue
                if colonadr.count(":") == 1 and obj.endswith(".obj"):
                    yield "%s %s %s\n" % (adr, dummy, name[1:])

        def readline(self):
            try:
                return self.generator.next()
            except StopIteration:
                return ""

        def close(self):
            self.file.close()
            
        def __iter__(self):
            return self.generator


re_addr = re.compile(r'[\s,$]0x([0-9a-fA-F]+)')
re_lineaddr = re.compile(r'\s*0?x?([0-9a-fA-F]+)')


symbols = {}
#rawtargets = {}
codeboundary = []

try:
    from xamsupport import any_pointer
except ImportError:
    def any_pointer(addr0, data, start, end, unpack=struct.unpack):
        for i in range(4, len(data)+1):
            offset, = unpack('l', data[i-4:i])
            if start <= addr0+i+offset < end or start <= offset < end:
                return 1
        return 0

def machine_code_dump(data, originaddr, format):
    if format == 'ivm':
        import ivmdump
        result = ivmdump.dump(data, originaddr)
    elif format == 'i386':
        f = open(tmpfile, 'wb')
        f.write(data)
        f.close()
        try:
            g = os.popen(objdump % {'file': tmpfile, 'origin': originaddr}, 'r')
            result = g.readlines()
            g.close()
        finally:
            os.unlink(tmpfile)
    return result

def load_symbol_file(filename, symb1, addr1):
    d = {}
    if type(symbollister) is str:
        g = os.popen(symbollister % filename, "r")
    else:
        g = symbollister(filename)
    while 1:
        line = g.readline()
        if not line:
            break
        match = re_symbolentry.match(line)
        if match:
            d[match.group(2)] = long(match.group(1), 16)
    g.close()
    if d.has_key(symb1):
        delta = addr1 - d[symb1]
    else:
        delta = 0
        print >> sys.stderr,"Warning: no symbol '%s' in '%s'" % (symb1, filename)
    for key, value in d.items():
        symbols[value + delta] = key


def symtext(sym, addr, inbuf=None, lineaddr=None):
    if isinstance(sym, CodeBuf):
        if sym is inbuf:
            name = 'top'
        else:
            name = '%s codebuf 0x%x' % (sym.mode, sym.addr)
        if addr > sym.addr:
            name += ' + %d' % (addr-sym.addr)
        return name
    else:
        return sym

revmap = {}
for key, value in htmlentitydefs.entitydefs.items():
    if type(value) is type(' '):
        revmap[value] = '&%s;' % key

def htmlquote(text):
    return ''.join([revmap.get(c,c) for c in text])

def lineaddresses(line):
    result = []
    i = 0
    while 1:
        match = re_addr.search(line, i)
        if not match:
            break
        i = match.end()
        addr = long(match.group(1), 16)
        result.append(addr)
    return result

def codeat(addr):
    i = bisect.bisect(codeboundary, (addr, None))
    if i>0:
        addrend, codebuf = codeboundary[i-1]
        if isinstance(codebuf, CodeBuf):
            return codebuf


re_int = re.compile(r"(\-?\d+)$")
re_ctvinfo = re.compile(r"ct (\d+) (\-?\d+)$")
re_rtvinfo = re.compile(r"rt (\-?\d+)$")
re_vtvinfo = re.compile(r"vt 0x([0-9a-fA-F]+)$")

LOC_LOCALS_PLUS = 3

class CodeBuf:
    __slots__ = ['mode', 'co_filename', 'co_name', 'nextinstr', 'addr',
                 'stackdepth', 'specdict', 'data', 'cache_text',
                 'disass_text', 'reverse_lookup', 'vlocals',
                 'complete_list', 'dumpfile', 'vlocalsofs', 'codemap']
    machine_code_format = '?'
    
    def __init__(self, mode, co_filename, co_name, nextinstr,
                 addr, stackdepth):
        self.mode = mode
        self.co_filename = co_filename
        self.co_name = co_name
        self.nextinstr = nextinstr
        self.addr = addr
        #self.data = data
        self.stackdepth = stackdepth
        #self.reverse_lookup = []  # list of (offset, codebuf pointing there)
        self.specdict = []
        if self.mode != "proxy":
            codeboundary.append((self.addr-0.5, self))
        else:
            self.data = ""
        #for i in range(4, len(data)+1):
        #    offset, = struct.unpack('l', data[i-4:i])
        #    rawtargets.setdefault(addr+i+offset, {})[self] = 1

    def getboundary(self):
        i = bisect.bisect(codeboundary, (self.addr-0.5, self))
        prev = codeboundary[i-1][1]
        next = codeboundary[i][1]
        #while not isinstance(next, BigBuffer) and next.addr == self.addr:
        #    i = i + 1
        #    next = codeboundary[i][1]
        while not isinstance(codeboundary[i][1], BigBuffer):
            i = i + 1
        bigbuf = codeboundary[i][1]
        return prev, next, bigbuf

    def splitheader(self):
        data = self.data
        addr = self.addr
        k = 0
        while data[k:k+1] == '\xCC':
            k = k + 1
        if data[k:k+4] == '\x66\x66\x66\x66':
            # detected a rt_local_buf_t structure
            next, key = struct.unpack('LL', data[k+4:k+12])
            data = data[k+12:]
            addr += k+12
        else:
            next = key = None
        return data, addr, next, key

    def __getattr__(self, attr):
        if attr == 'data':
            prev, next, bigbuf = self.getboundary()
            assert prev is self
            self.data = data = bigbuf.load(self.addr, next.addr)
            return data
        if attr == 'cache_text':
            # produce the disassembly listing
            data, addr, next, key = self.splitheader()
            self.cache_text = []
            if key is not None:
                self.cache_text.append(
                    'Created by promotion of the value 0x%x\n' % key)
            if next is not None:
                self.cache_text.append(
                    'Next promoted value at buffer 0x%x\n' % next)
            self.cache_text += machine_code_dump(data, addr,
                                                 CodeBuf.machine_code_format)
            return self.cache_text
        if attr == 'disass_text':
            txt = self.cache_text
            if self.specdict:
                txt.append('\n')
                txt.append("'do_promotion' dictionary:\n")
                for key, value in self.specdict:
                    txt.append('.\t%s:\t\t\n' % htmlquote(key))
                    txt.append('.\t\t0x%x\t\t\n' % value)
            self.disass_text = txt
            return txt
        if attr == 'reverse_lookup':
            # 'reverse_lookup' is a list of (offset, codebuf pointing there)
            self.reverse_lookup = []
            start = self.addr
            end = start + len(self.data)
            for codebuf in self.complete_list:
                if any_pointer(codebuf.addr, codebuf.data, start, end):
                    for line in codebuf.disass_text:
                        for addr in lineaddresses(line):
                            if start <= addr < end:
                                self.reverse_lookup.append((addr-start, codebuf))
            return self.reverse_lookup
        if attr == 'vlocals':
            self.dumpfile.seek(self.vlocalsofs)
            self.vlocals = self.load_vi_array({0: None})
            return self.vlocals
        raise AttributeError, attr

    def load_vi_array(self, d):
        dumpfile = self.dumpfile
        match = re_int.match(dumpfile.readline())
        assert match
        count = int(match.group(1))
        a = []
        for i in range(count):
            line = dumpfile.readline()
            match = re_int.match(line)
            assert match
            addr = long(match.group(1))
            if d.has_key(addr):
                vi = d[addr]
            else:
                line = dumpfile.readline()
                match = re_ctvinfo.match(line)
                if match:
                    vi = CompileTimeVInfo(int(match.group(1)),
                                          long(match.group(2)))
                else:
                    match = re_rtvinfo.match(line)
                    if match:
                        vi = RunTimeVInfo(long(match.group(1)), self.stackdepth)
                    else:
                        match = re_vtvinfo.match(line)
                        assert match
                        vi = VirtualTimeVInfo(long(match.group(1), 16))
                d[addr] = vi
                vi.addr = addr
                vi.array = self.load_vi_array(d)
            a.append(vi)
        a.reverse()
        return a

    def get_next_instr(self):
        if self.nextinstr >= 0:
            return self.nextinstr

    def spec_dict(self, key, value):
        self.specdict.append((key, value))
        #rawtargets.setdefault(value, {})[self] = 1
        try:
            del self.disass_text
        except:
            pass
        try:
            del self.reverse_lookup
        except:
            pass
    
##    def build_reverse_lookup(self):
##        for line in self.disass_text:
##            for addr in lineaddresses(line):
##                sym = symbols.get(addr)
##                if isinstance(sym, CodeBuf):
##                    sym.reverse_lookup.append((addr-sym.addr, self))
    
    def disassemble(self, symtext=symtext, linetext=None, snapshot=None):
        seen = {}
        data = []
        for line in self.disass_text:
            if line.endswith('\n'):
                line = line[:-1]
            match = re_lineaddr.match(line)
            if match:
                lineaddr = long(match.group(1), 16)
                if not seen.has_key(lineaddr):
                    if self.codemap.has_key(lineaddr) and snapshot:
                        for proxy in self.codemap[lineaddr]:
                            data.append(snapshot(proxy))
                    seen[lineaddr] = 1
                ofs = lineaddr - self.addr
                sources = [c for o, c in self.reverse_lookup if o == ofs]
                if sources and linetext:
                    line = linetext(line, lineaddr)
                if sources != [self]*len(sources):
                    data.append('\n')
            else:
                lineaddr = None
            for addr in lineaddresses(line):
                sym = symbols.get(addr) or codeat(addr)
                if sym:
                    line = '%s\t(%s)' % (line, symtext(sym, addr, self,lineaddr))
                    break
            data.append(line + '\n')
        return ''.join(data)


class BigBuffer:
    __slots__ = ['file', 'offset', 'start', 'length', 'addr', 'priority']
    def __init__(self, file, start, length):
        #if sys.stderr.softspace:
        #    print >> sys.stderr
        #print >> sys.stderr, 'BigBuffer:', hex(start), hex(start+length),
        #print >> sys.stderr, '(%d)' % length
        self.file = file
        self.offset = file.tell()
        self.start = start
        self.length = length
        self.addr = start + length   # end address
        self.priority = -len(codeboundary)
        codeboundary.append((self.addr-0.25, self))
        file.seek(self.length, 1)
    def load(self, begin, end):
        assert self.start <= begin <= self.addr, \
               (hex(self.start), hex(begin), hex(end), hex(self.addr))
        self.file.seek(self.offset + (begin-self.start))
        return self.file.read(min(self.addr, end) - begin)


class VInfo:
    __slots__ = ['addr', 'array']

class CompileTimeVInfo(VInfo):
    __slots__ = ['flags', 'value']
    def __init__(self, flags, value):
        self.flags = flags
        self.value = value
    def gettext(self):
        text = "Compile-time value 0x%x" % self.value
        if self.flags & 1:
            text += ", fixed"
        if self.flags & 2:
            text += ", reference"
        return text
    def getsummarytext(self):
        text = "Compile-time"
        if self.flags & 1:
            text += " fixed"
        text += " 0x%x" % self.value
        return text

class RunTimeVInfo(VInfo):
    __slots__ = ['source', 'stackdepth']
    REG_NAMES = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
    def __init__(self, source, stackdepth=None):
        self.source = source
        self.stackdepth = stackdepth
    def gettext(self):
        text = "Run-time source,"
        reg = self.source >> 28
        stack = self.source & 0x03FFFFFC
        if CodeBuf.machine_code_format == 'ivm':
            if reg:
                text += " in a register ??????"
            if not stack:
                text += " not in stack ??????"
            else:
                text += " in stack [%d] or from top #%d" % (
                    (self.stackdepth-stack)/4,
                    stack/4)
        else:
            if 0 <= reg < 8:
                text += " in register %s" % self.REG_NAMES[reg].upper()
                if stack:
                    text += " and"
            if stack:
                if self.stackdepth is None:
                    sd = ""
                else:
                    sd = "[ESP+0x%x] or " % (self.stackdepth - stack)
                text += " in stack %sfrom top %d" % (sd, stack)
        if not (self.source & 0x08000000):
            text += " holding a reference"
        if self.source & 0x04000000:
            text += " >=0"
        return text
    def getsummarytext(self):
        return "Run-time"

class VirtualTimeVInfo(VInfo):
    __slots__ = ['vs']
    def __init__(self, vs):
        self.vs = vs
    def gettext(self):
        return "Virtual-time source (%x)" % self.vs
    def getsummarytext(self):
        return "Virtual-time (%x)" % self.vs

def readdump(filename = 'psyco.dump'):
    del codeboundary[:]
    re_header = re.compile(r"Psyco dump [[](\w+?)[]]")
    re_symb1 = re.compile(r"(\w+?)[:]\s0x([0-9a-fA-F]+)")
    re_codebuf = re.compile(r"CodeBufferObject 0x([0-9a-fA-F]+) (\-?\d+) \'(.*?)\' \'(.*?)\' (\-?\d+) \'(.*?)\'$")
    re_specdict = re.compile(r"spec_dict 0x([0-9a-fA-F]+)")
    re_vinfo_array = re.compile(r"vinfo_array")
    re_spec1 = re.compile(r"0x([0-9a-fA-F]+)\s(.*)$")
    re_bigbuffer = re.compile(r"BigBuffer 0x([0-9a-fA-F]+) (\d+)$")
    
    codebufs = []
    dumpfile = open(filename, 'rb')
    match = re_header.match(dumpfile.readline())
    if not match:
        raise ValueError, "'%s' does not look like a Psyco dump" % filename
    CodeBuf.machine_code_format = match.group(1)
    
    bufcount, = struct.unpack("i", dumpfile.read(4))
    buftable = list(struct.unpack("l"*bufcount, dumpfile.read(4*bufcount)))
    buftable.reverse()
    if buftable:
        filesize = buftable[-1]
    else:
        filesize = sys.maxint
    filesize *= 1.0
    nextp = 0.1
    cbsortedsize = 0
    for filename in symbolfiles:
        line = dumpfile.readline()
        match = re_symb1.match(line)
        assert match
        load_symbol_file(filename, match.group(1), long(match.group(2), 16))
    while 1:
        line = dumpfile.readline()
        if not line:
            print "Note: unexpected end of file"
            break
        #print line.strip()
        match = re_codebuf.match(line)
        if match:
            percent = dumpfile.tell() / filesize
            if percent >= nextp:
                print >> sys.stderr, '%d%%...' % int(100*percent),
                nextp += 0.1
            #size = int(match.group(2))
            #data = dumpfile.read(size)
            #assert len(data) == size
            codebuf = CodeBuf(match.group(6), match.group(3), match.group(4),
                              int(match.group(5)), long(match.group(1), 16),
                              int(match.group(2)))
            codebuf.dumpfile = dumpfile
            codebuf.vlocalsofs = buftable.pop()
            codebufs.append(codebuf)
        else:
            match = re_specdict.match(line)
            if match:
                addr = long(match.group(1), 16)
                if len(codeboundary) != cbsortedsize:
                    codeboundary.sort()
                    cbsortedsize = len(codeboundary)
                codebuf = codeat(addr-4)
                if codebuf is None:
                    raise "spec_dict with no matching code buffer", line
                while 1:
                    line = dumpfile.readline()
                    if len(line)<=1:
                        break
                    match = re_spec1.match(line)
                    assert match
                    codebuf.spec_dict(match.group(2), long(match.group(1), 16))
            elif re_vinfo_array.match(line):
                assert len(codebufs) == bufcount
                break
            else:
                match = re_bigbuffer.match(line)
                if match:
                    BigBuffer(dumpfile, long(match.group(1), 16),
                              int(match.group(2)))
                else:
                    raise "invalid line", line
    print >> sys.stderr, 'sorting...',
    if len(codeboundary) != cbsortedsize:
        codeboundary.sort()
    codemap = {}
    #cblist = []
    codebufs.reverse()
    for codebuf in codebufs:
        codebuf.complete_list = codebufs
        codebuf.codemap = codemap
        codemap.setdefault(codebuf.addr, []).insert(0, codebuf)
        #prev, next, bigbuf = codebuf.getboundary()
        #cblist.append((bigbuf.priority, codebuf.addr, codebuf))
    #cblist.sort()
    #codebufs[:] = [codebuf for priority, addr, codebuf in cblist]
    print >> sys.stderr, '100%'
    return codebufs

if __name__ == '__main__':
    if len(sys.argv) > 1:
        codebufs = readdump(sys.argv[1])
    else:
        codebufs = readdump()
    for codebuf in codebufs:
        print codebuf.disassemble()
