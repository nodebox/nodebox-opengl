import sys, re, cStringIO, os, dis, types, struct
import xam, psyco
from SimpleHTTPServer import SimpleHTTPRequestHandler, test

#
# Adapted from SimpleHTTPServer.py.
#

def show_vinfos(array, d, co=None, path=[]):
    text = "<ol>"
    for i in range(len(array)):
        vi = array[i]
        text += "<li>"
        if hasattr(co, 'co_code') and path == []:
            j = i - xam.LOC_LOCALS_PLUS
            if 0 <= j < len(co.co_varnames):
                text += "(%s):\t" % co.co_varnames[j]
        #if name is not None:
        #    text += "%s " % name
        if vi is None:
            text += "[NULL]"
        else:
            text += "[%x] %s" % (vi.addr, vi.gettext())
            if d.has_key(vi.addr):
                text += " (already seen above)"
            else:
                d[vi.addr] = 1
            if vi.array:
                text += show_vinfos(vi.array, d, co, path+[i])
        text += '</li>\n'
    text += '</ol>\n'
    return text

def summary_vinfos(array, d, path=[]):
    text = ''
    indent = '  ' * len(path)
    for i in range(len(array)):
        vi = array[i]
        text += indent
        if vi is None:
            text += "[NULL]\n"
        else:
            text += "%d. %s" % (i, vi.getsummarytext())
            if d.has_key(vi.addr):
                text += " (already seen above)"
            else:
                d[vi.addr] = 1
            text += '\n'
            if vi.array:
                text += summary_vinfos(vi.array, d, path+[i])
    return text

def find4(f, s4):
    result = []
    while 1:
        base = f.tell()
        buffer = f.read(8192)
        if not buffer:
            return result
        p = -1
        while 1:
            p = buffer.find(s4, p+1)
            if p<0:
                break
            if not (p&3):
                result.append(base + p)

re_codebuf = re.compile(r'[/]0x([0-9A-Fa-f]+)$')
re_proxy   = re.compile(r'[/]proxy(\d+)$')
re_summary = re.compile(r'[/]summary(\d+)$')
re_trace   = re.compile(r'[/]trace0x([0-9A-Fa-f]+)$')
re_traces  = re.compile(r'[/]traces0x([0-9A-Fa-f]+)$')
re_trlist  = re.compile(r'[/]trace0x([0-9A-Fa-f]+)[-]0x([0-9A-Fa-f]+)$')

##def cache_load(filename, cache={}):
##    try:
##        return cache[filename]
##    except KeyError:
##        data = {}
##        try:
##            f = execfile(filename, data)
##        except:
##            data = None
##        cache[filename] = data
##        return data

def cache_load(filename, codename, cache={}):
    try:
        modulecode = cache[filename]
    except KeyError:
        source = None
        try:
            f = open(filename, 'rU')
            source = f.read()
            f.close()
            modulecode = compile(source, filename, 'exec')
        except Exception, e:
            print repr(source)
            print '*** While loading %s:' % (filename,)
            import traceback
            traceback.print_exc()
            return None

    return recfindcode(modulecode, codename)

def recfindcode(code, codename):
    if code.co_name == codename:
        return code
    else:
        for c in code.co_consts:
            if type(c) is type(code):
                result = recfindcode(c, codename)
                if result:
                    return result
    return ''


class CodeBufHTTPHandler(SimpleHTTPRequestHandler):

    def symhtml(self, sym, addr, inbuf=None, lineaddr=None):
        text = xam.symtext(sym, addr, inbuf, lineaddr)
        if isinstance(sym, xam.CodeBuf):
            if addr == sym.addr:
                name = ''
            else:
                name = '#0x%x' % addr
            text = "<a href='/0x%x%s'>%s</a>" % (sym.addr, name, text)
        if addr == lineaddr:
            text += "\t<a href='/traces0x%x'>traces</a>" % addr
        return text

    def linehtml(self, line, addr):
        line = "<a name='0x%x'><strong>%s</strong></a>" % (addr, line)
        if addr in self.trace_addr:
            line = "<font color='#FF0000'>%s</font>" % line
            i = self.trace_addr.index(addr)
            if i == 0 and self.trace_prev is not None:
                line += ("\t<a href='/trace0x%x'>&lt;&lt;&lt;&lt;&lt;</a>" %
                         self.trace_prev)
            if i == len(self.trace_addr)-1 and self.trace_next is not None:
                line += ("\t<a href='/trace0x%x'>&gt;&gt;&gt;&gt;&gt;</a>" %
                         self.trace_next)
        return line

    def proxyhtml(self, proxy):
        return "<a href='/proxy%d'>(snapshot %s:%s)</a>\n" % (
            codebufs.index(proxy), proxy.co_name, proxy.get_next_instr())

    def htmlpage(self, title, data):
        return ('<html><head><title>%s</title></head>\n'  % title
                + '<body><h1>%s</h1>\n'               % title
              # + '<hr>\n'
                + data
                + '<hr></body>\n')

    def bufferpage(self, codebuf):
        rev = {}
        for o, c in codebuf.reverse_lookup:
            if c is not codebuf:
                rev[c] = rev.get(c,0) + 1
        if rev:
            data = '<p>Other code buffers pointing to this one:</p><ul>\n'
            for c in codebufs:  # display them in original load order
                if rev.has_key(c):
                    if rev[c] == 1:
                        extra = ''
                    else:
                        extra = '\t(%d times)' % rev[c]
                    data += '<li>%s\t(%d bytes)%s</li>\n' %  \
                            (self.symhtml(c, c.addr),
                             len(c.data),
                             extra)
            data += '</ul>\n'
        else:
            data = '<p>No other code buffer points to this one.</p>\n'
        data += '<hr>\n'
        data += '<pre>%s</pre>\n' % codebuf.disassemble(self.symhtml,
                                                        self.linehtml,
                                                        self.proxyhtml)
        data += "<br><a href='/'>Back to the list of code objects</a>\n"
        if codebuf.co_name:
            data = '<p>Code object %s from file %s, at position %s</p>%s' % (
                codebuf.co_name, codebuf.co_filename, codebuf.get_next_instr(),
                data)
        return data

    def try_hard_to_name(self, addr):
        def result(codebuf):
            return '%s:%s:%s' % (codebuf.co_filename, codebuf.co_name,
                                 codebuf.get_next_instr())
        codebuf = xam.codeat(addr)
        if codebuf is not None:
            codemap = codebuf.codemap
            proxylist = []
            for lineaddr in range(addr, codebuf.addr-1, -1):
                if codemap.has_key(lineaddr):
                    for proxy in codemap[lineaddr]:
                        if proxy.co_name:
                            return result(proxy)
        if codebuf.co_name:
            return result(codebuf)
        else:
            return '?'

    def send_head(self):
        global codebufs # CT
        self.trace_prev = None
        self.trace_next = None
        self.trace_addr = ()
        
        if self.path == '/' or self.path == '/all':
            all = self.path == '/all'
            if all:
                title = 'List of ALL code objects'
            else:
                title = 'List of all named code objects'
            data = ['<ul>']
            named = 0
            proxies = 0
            for codebuf in codebufs:
                if codebuf.data and codebuf.co_name:
                    named += 1
                else:
                    if not codebuf.data:
                        proxies += 1
                    if not all:
                        continue
                data.append('<li>%s:\t%s:\t%s:\t%s\t(%d bytes)</li>\n' % (
                    codebuf.co_filename, codebuf.co_name,
                    codebuf.get_next_instr(),
                    self.symhtml(codebuf, codebuf.addr),
                    len(codebuf.data)))
            data.append('</ul>\n')
            data.append('<br><a href="/">%d named buffers</a>; ' % named +
                     '<a href="/all">%d buffers in total</a>, ' % len(codebufs) +
                     'including %d proxies' % proxies)
            data = ''.join(data)
            return self.donepage(title, data)

        match = re_codebuf.match(self.path)
        if match:
            addr = long(match.group(1), 16)
            codebuf = xam.codeat(addr)
            if not codebuf:
                self.send_error(404, "No code buffer at this address")
                return None
            if codebuf.addr != addr:
                self.trace_addr = [addr]
            title = '%s code buffer at 0x%x' % (codebuf.mode.capitalize(),
                                                codebuf.addr)
            data = self.bufferpage(codebuf)
            return self.donepage(title, data)

        match = re_trace.match(self.path)
        if match:
            tracepos = int(match.group(1), 16)
            f = open(tracefilename, 'rb')
            try:
                def traceat(p, f=f):
                    f.seek(p)
                    data = f.read(4)
                    if len(data) == 4:
                        addr, = struct.unpack('L', data)
                        return addr
                    else:
                        raise IOError
                addr = traceat(tracepos)
                codebuf = xam.codeat(addr)
                if not codebuf:
                    self.send_error(404, "No code buffer at 0x%x" % addr)
                    return None
                start = codebuf.addr
                end = start + len(codebuf.data)
                while tracepos > 0:
                    addr1 = traceat(tracepos-4)
                    if not (start <= addr1 < addr):
                        break
                    tracepos -= 4
                    addr = addr1
                self.trace_prev = tracepos-4
                self.trace_addr = []
                while 1:
                    self.trace_addr.append(addr)
                    addr1 = traceat(tracepos+4)
                    if not (addr < addr1 < end):
                        break
                    tracepos += 4
                    addr = addr1
                self.trace_next = tracepos+4
            finally:
                f.close()
            title = '%s code buffer at 0x%x' % (codebuf.mode.capitalize(),
                                                codebuf.addr)
            data = self.bufferpage(codebuf)
            return self.donepage(title, data)

        match = re_traces.match(self.path)
        if match:
            traceaddr = long(match.group(1), 16)
            f = open(tracefilename, 'rb')
            plist = find4(f, struct.pack('L', traceaddr))
            f.close()
            title = 'Traces through 0x%x' % traceaddr
            data = ['<ul>']
            for p in plist:
                data.append("<li><a href='/trace0x%x'>0x%x</a>\n" % (p, p))
            data.append('</ul>')
            data = ''.join(data)
            return self.donepage(title, data)

        match = re_trlist.match(self.path)
        if match:
            start = int(match.group(1), 16)
            end   = int(match.group(2), 16)
            title = 'Traces timed 0x%x to 0x%x' % (start, end)
            data = ["<p><a href='/trace0x%x-0x%x'>&lt;&lt;&lt;&lt;</a></p>\n" %
                    (start-(end-start), start),
                    '<ul>']
            f = open(tracefilename, 'rb')
            f.seek(start)
            prevname = None
            for p in range(start, end, 4):
                addr, = struct.unpack('L', f.read(4))
                s = self.try_hard_to_name(addr)
                if s == prevname:
                    continue
                data.append("<li><a href='/trace0x%x'>0x%x: %s</a>\n" % (p,p,s))
                prevname = s
            data.append('</ul>')
            data.append(
                "<p><a href='/trace0x%x-0x%x'>&gt;&gt;&gt;&gt;</a></p>\n" %
                (end, end+(end-start)))
            f.close()
            data = ''.join(data)
            return self.donepage(title, data)

        match = re_proxy.match(self.path)
        if match:
            title = 'Snapshot'
            n = int(match.group(1))
            proxy = codebufs[n]
            for n1 in xrange(n-1, -1, -1):
                pprev = codebufs[n1]
                if (pprev.nextinstr == proxy.nextinstr and
                    pprev.co_name == proxy.co_name and
                    pprev.co_filename == proxy.co_filename):
                    pprev = n1
                    break
            else:
                pprev = None
            for n1 in xrange(n+1, len(codebufs)):
                pnext = codebufs[n1]
                if (pnext.nextinstr == proxy.nextinstr and
                    pnext.co_name == proxy.co_name and
                    pnext.co_filename == proxy.co_filename):
                    pnext = n1
                    break
            else:
                pnext = None
            filename = os.path.join(DIRECTORY, proxy.co_filename)
            co = cache_load(filename, proxy.co_name)
            data = '<p>PsycoObject structure at this point:'
            data += '&nbsp;' * 20
            data += '['
            data += '&nbsp;&nbsp;<a href="summary%d">summary</a>&nbsp;&nbsp;' % n
            if pprev is not None or pnext is not None:
                if pprev is not None:
                    data += '&nbsp;&nbsp;<a href="proxy%d">&lt;&lt;&lt; previous</a>&nbsp;&nbsp;' % pprev
                if pnext is not None:
                    data += '&nbsp;&nbsp;<a href="proxy%d">next &gt;&gt;&gt;</a>&nbsp;&nbsp;' % pnext
            data += ']'
            data += '</p>\n'
            data += show_vinfos(proxy.vlocals, {}, co)
            data += '<hr><p>Disassembly of %s:%s:%s:</p>\n' % (
                proxy.co_filename, proxy.co_name, proxy.get_next_instr())
            if co is None: #moduledata is None:
                txt = "(exception while loading the file '%s')\n" % (
                    filename)
            else:
                if not hasattr(co, 'co_code'):
                    txt = "(no function object '%s' in file '%s')\n" % (
                        proxy.co_name, filename)
                else:
                    txt = cStringIO.StringIO()
                    oldstdout = sys.stdout
                    try:
                        sys.stdout = txt
                        dis.disassemble(co, proxy.get_next_instr())
                    finally:
                        sys.stdout = oldstdout
                    txt = txt.getvalue()
            data += '<pre>%s</pre>\n' % txt
            data += "<br><a href='/0x%x'>Back</a>\n" % proxy.addr
            return self.donepage(title, data)

        match = re_summary.match(self.path)
        if match:
            n = int(match.group(1))
            proxy = codebufs[n]
            data = summary_vinfos(proxy.vlocals, {})
            f = cStringIO.StringIO(data)
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            return f

        if self.path == '/checkall':
            for codebuf in codebufs:
                codebuf.cache_text
            f = cStringIO.StringIO('done')
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            return f

        ## CT: simple reload feature
        if self.path == "/reload":
            codebufs = xam.readdump(FILENAME)
            self.path = "/all"
            return self.send_head()
        
        self.send_error(404, "Invalid path")
        return None

    def donepage(self, title, data):
        f = cStringIO.StringIO(self.htmlpage(title, data))
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        return f


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print "Usage: python httpxam.py <directory>"
        print "  psyco.dump and any .py files containing code objects"
        print "  are loaded from the <directory>."
        sys.exit(1)
    DIRECTORY = sys.argv[1]
    del sys.argv[1]
    filename = os.path.join(DIRECTORY, 'psyco.dump')
    if not os.path.isfile(filename) and os.path.isfile(DIRECTORY):
        filename = DIRECTORY
        DIRECTORY = os.path.dirname(DIRECTORY)
    tracefilename = os.path.join(DIRECTORY, 'psyco.trace')
    codebufs = xam.readdump(filename)
    FILENAME = filename # CT hack
    test(CodeBufHTTPHandler)
