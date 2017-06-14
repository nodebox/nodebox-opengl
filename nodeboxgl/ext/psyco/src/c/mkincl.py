import sys, os

def getincl():
    PY_VER = sys.version[:3]
    for p in (sys.prefix, sys.exec_prefix):
        if sys.executable.startswith(p):
            return [os.path.join(sys.prefix, 'include', 'python'+PY_VER)]
    base = os.path.dirname(sys.executable)
    if os.path.exists(os.path.join(base, 'Include')):
        return [os.path.join(base, 'Include'), base, os.path.join(base, 'Stackless')]
    raise IOError, 'cannot find the include directories for %s' % sys.executable

INCLUDE_STR = ' '.join(['-I%s' % s for s in getincl()])

if __name__ == '__main__':
    print INCLUDE_STR
