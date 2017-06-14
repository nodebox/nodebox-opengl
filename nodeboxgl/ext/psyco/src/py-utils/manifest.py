from __future__ import generators
import os
import py   # the py lib, see http://codespeak.net/py

def psycofiles():
    path = py.path.svnwc(os.pardir)
    for p in path.visit(lambda x: x.check(versioned=1)):
        if p.check(dir=1):
            print p
        else:
            yield p.relto(path)

def generate():
    filename = os.path.join('..', 'MANIFEST')
    print 'Rebuilding %s...' % filename
    lst = list(psycofiles())
    lst.sort()
    f = open(filename, 'w')
    for filename in lst:
        print >> f, filename
    f.close()

if __name__ == '__main__':
    generate()
