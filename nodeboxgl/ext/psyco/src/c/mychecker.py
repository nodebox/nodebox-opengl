import re, dis
recase = re.compile(r'case\s+([A-Z_][A-Z_+0-9]*)\s*[:]')
rebin  = re.compile(r'BINARY_OPCODE[(]([A-Z_][A-Z_+0-9]*),')
remiss = re.compile(r'[/*]*MISSING_OPCODE[(]([A-Z_][A-Z_+0-9]*)[)]')

if dis.opname[86] == 'YIELD_STMT':
    dis.opname[86] = 'YIELD_VALUE'

inswitch = 0
lst = []
miss = []
warn = 0

def register(op):
    global warn
    print "%29s" % op,
    if op not in lst:
        lst.append(op)
    if op not in dis.opname:
        print "%29s" % "<--- unknown opcode",
        #warn += 1
    print

print "+++ Found +++"
print

for line in open('Python/pycompiler.c').readlines():
    line = line.strip()
    if line.startswith('switch (opcode)'):
        inswitch = 1
    elif line.endswith('/* switch (opcode) */'):
        inswitch = 0
    elif inswitch:
        m = recase.match(line) or rebin.match(line)
        if m:
            register(m.group(1))
        else:
            m = remiss.match(line)
            if m:
                miss.append(m.group(1))
print
print

assert not inswitch

print '+++ Not implemented +++'
print
for i, opname in zip(range(1,256), dis.opname[1:]):
    if not opname.startswith('<') and opname not in lst:
        print "%4d %29s" % (i, opname),
        if opname not in miss:
            print "%29s" % "<--- forgotten ?",
            warn += 1
        else:
            miss.remove(opname)
        print
print

for opname in miss:
    print "%29s" % opname, "%29s" % "<--- marked as missing, don't know why"

print

for line in open('mergepoints.c').readlines():
    for word in lst:
        if line.find(word) >= 0:
            lst.remove(word)
            break

for word in lst:
    print '!!! Not found in mergepoints.c !!!'
    print
    print word
    print
    warn += 1

if warn:
    print '                               !!! %d warning(s) !!!' % warn
