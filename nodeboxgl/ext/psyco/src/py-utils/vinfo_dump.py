from xam import *
import httpxam


def load_vi_array(dumpfile, d):
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
                    vi = RunTimeVInfo(long(match.group(1)))
                else:
                    match = re_vtvinfo.match(line)
                    assert match
                    vi = VirtualTimeVInfo(long(match.group(1), 16))
            d[addr] = vi
            vi.addr = addr
            vi.array = load_vi_array(dumpfile, d)
        a.append(vi)
    a.reverse()
    return a

def main(dumpfile):
    import os, tempfile
    array = load_vi_array(dumpfile, {0: None})
    text = httpxam.show_vinfos(array, {})
    if os.fork() == 0:
        TMP = tempfile.mktemp('.html')
        g = open(TMP, 'w')
        g.write('<html><head></head><body>\n')
        g.write(text)
        g.write('</body>\n')
        g.close()
        try:
            os.system('xterm -e lynx -force_html %s' % TMP)
        finally:
            os.unlink(TMP)

if __name__ == '__main__':
    import sys
    main(sys.stdin)
