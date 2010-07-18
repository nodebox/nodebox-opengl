#from __future__ import generators
#from __future__ import division
import psyco, os, sys, array, operator, traceback
from time import sleep, clock

def time(fn, *args):
    "Measure the execution time of fn(*args)."
    begin = clock()
    try:
        result  = apply(fn, args)
    except:
        end = clock()
        traceback.print_exc()
        result = '<exception>'
    else:
        end = clock()
    return result, end-begin


ZERO = 0

def f1(n):
    "Arbitrary test function."
    i = 0
    x = 1
    while i<n:
        j = ZERO
        while j<=i:
            j = j + 1
            x = x + (i&j)
        i = i + 1
    return x

def f2(x):
    "Trivial function."
    return x*2

def f3(n):
    "Prints f2(x) on all non-null items of the sequence n."
    for x in n:
        if x == 0:
            continue
        print f2(x)

def f4(filelist):
    "Count all characters of all files whose names are in filelist."
    result = [0]*256
    for filename in filelist:
        f = open(filename, 'r')
        for line in f:
            for c in line:
                k = ord(c)
                result[k] = result[k] + 1
        f.close()
    d = {}
    for i in range(256):
        if result[i]:
            d[chr(i)] = result[i]
    return d

def f5(filelist):
    "Same as f4() but completely loads the files in memory."
    result = [0]*256
    for filename in filelist:
        f = open(filename, 'r')
        for c in f.read():
            k = ord(c)
            result[k] = result[k] + 1
        f.close()
    d = {}
    for i in range(256):
        if result[i]:
            d[chr(i)] = result[i]
    return d

def f6(n, p):
    "Computes the factorial of n modulo p."
    factorial = 1
    for i in range(2, n+1):
        factorial = (factorial * i) % p
    return factorial

def mandelbrot(c):
    za, zb = c.real, c.imag
    for i in range(1000):
        za2 = za*za
        zb2 = zb*zb
        if za2+zb2 > 4.0:
            if i > 126-33: i = 126-33
            return chr(33+i)
        za, zb = za2-zb2+c.real, 2*za*zb+c.imag
        del za2, zb2
    return " "

def f7(start, end, step):
    "Computes the Mandelbrot set. All args are complex numbers."
    width = int((end.real - start.real) / step.real)
    while start.imag < end.imag:
        line = [mandelbrot(start + n*step.real) for n in range(width)]
        print ''.join(line)
        start += complex(0, step.imag)

def f8():
    try:
        x = 1.0 / 0.0
    #except StandardError, e:
    #    print "in except clause:", e
    finally:
        print "in finally clause"
        x = 5
    print "x is now", x

def f9(n):
    for i in range(n):
        print i,
    print

def f10():
    apply(f9, (50,))


def go(f, *args):
    print '-'*80
    v1, t1 = time(psyco.proxy(f), *args)
    print v1
    print '^^^ computed by Psyco in %s seconds' % t1
    v2, t2 = time(f, *args)
    if v1 == v2:
        if t1 and t2:
            s = ', Psyco is %.2f times faster' % (t2/float(t1))
        else:
            s = ''
        print 'Python got the same result in %s seconds%s' % (t2, s)
    else:
        print v2
        print '^^^ by Python in %s seconds' % t2
        print '*'*80
        print '!!! different results !!!'

def go1(arg=2117):
    go(f1, arg)

FILEPATH = '../c'
FILELIST = [os.path.join(FILEPATH, s) for s in os.listdir(FILEPATH)]
FILELIST = [s for s in FILELIST if os.path.isfile(s) and s!='psyco.dump']

def go4(arg=FILELIST):
    go(f4, arg)

def go5(arg=FILELIST):
    go(f5, arg)

def go6(n=100000, p=100000000000001L):
    go(f6, n, p)

def go7(start=-2-1j, end=1+1j, step=0.04+0.08j):
    go(f7, start, end, step)


def f11(prefix):
    #prefix = [60, 115, 116, 114, 114, 114, 114, 62]
    
    table = [-1] + ([0]*len(prefix))
    for i in range(len(prefix)):
        table[i+1] = table[i]+1
        while table[i+1] > 0 and prefix[i] != prefix[table[i+1]-1]:
            table[i+1] = table[table[i+1]-1]+1
    #code.extend(table[1:]) # don't store first entry
    print table[1:]

def f12(arg):
    def g(x, y=arg):
        return x+y
    return g(123)

def f13(arg):
    x,y = arg
    print x, y
    u,v = x,y
    print u, v
    return v,u

def f15(x):
    print x

def f14(n):
    f15(n==5)

def f16(x):
    return ~x

def f17(x, y=0, *args):
    return x, y, args

#def f18():
#    yield 5
#    yield 6

def f19(seq):
    class C:
        def __init__(self):
            print "hello"
    c = C()
    seq = list(seq)
    seq1 = seq
    seq *= 3
    n = seq[0]
    n /= 3
    return seq, seq1 is seq, n

def f20(code, n, fill=0):
    a = array.array(code, [fill]*n)
    for i in range(n):
        item = i*10
        if code == 'c':
            item = chr(item)
        a[i] = item
    return [a[i] for i in range(len(a))]

def f21(lst):
    return operator.indexOf(lst, 9)

def f22(n):
    try:
        x = 1/n
    except:
        print "Catch!"

def f23(n):
    f22(n)
    try:
        x = undefined_name
    except:
        f22(n)
        print sys.exc_type.__name__

def f24(n):
    return 1/n

def f25(n):
    try:
        return f24(n)
    except AttributeError:
        auwsziazsi

def f26():
    import psyco.classes
    import array
    import urllib
    from types import FloatType, ListType
    from psyco.core import full
    return FloatType, ListType, urllib, psyco.classes, full

def test_getframe():
    import sys
    i = 0
    print 'test_getframe():'
    while 1:
        try:
            f = sys._getframe(i)
        except ValueError:
            break
        #print '%-26s %-60s %-40s' % (f, f.f_code, f.f_locals.keys())
        print f.f_code.co_name.replace('<module>', '?')
        i += 1

def test_getframe1():
    return test_getframe()
psyco.cannotcompile(test_getframe1)

def test_getframe_b():
    import sys
    i = 0
    print 'test_getframe_b():'
    f = sys._getframe()
    while f is not None:
        print f.f_code.co_name.replace('<module>', '?')
        f = f.f_back    # walk the stack with f_back

def test_getframe_b1():
    return test_getframe_b()
psyco.cannotcompile(test_getframe_b1)

def f28():
    test_getframe()
    return N

def f27():
    global N
    N = 5
    a = f28()
    N = 6
    b = f28()
    N = 7
    c = f28()
    return a,b,c

def f28_1():
    test_getframe1()
    return N

def f27_1():
    global N
    N = 51
    a = f28_1()
    N = 61
    b = f28_1()
    N = 71
    c = f28_1()
    return a,b,c

def f28_b():
    test_getframe_b()
    return N

def f27_b():
    global N
    N = 95
    a = f28_b()
    N = 96
    b = f28_b()
    N = 97
    c = f28_b()
    return a,b,c

def f28_b1():
    test_getframe_b1()
    return N

def f27_b1():
    global N
    N = 951
    a = f28_b1()
    N = 961
    b = f28_b1()
    N = 971
    c = f28_b1()
    return a,b,c

def f29(lst):
    lst = lst[:]
    del lst[2]
    lst[3] = 6
    return lst

def f30():
    Baz

def f31():
    f30()

def f32(p):
    if p[1:2] == ':':
        return p[0:2], p[2:]
    return '', p

def f33(n):
    if ((n+1) & n) == 0:
        print n

def f34(m=2000000):
    for i in xrange(m):
        f33(i)

def f35():
    try:
        import Numeric
    except ImportError:
        print "[[5 5 5]"
        print " [5 5 5]"
        print " [5 5 5]]"
    else:
        a = Numeric.zeros((3,3))
        a += 5
        print a

def f36():
    class X:
        pass
    class Y(X):
        pass
    return Y(), Y.__module__, __in_psyco__

def f37(x):
    print 'ZERO' in globals().keys()
    dir()
    print eval('ZERO+1')

def f38(n):
    f = f1
    r = [
        f(n, *[]),
        f(n),
        apply(f, (n,)),
        apply(f, [n]),
        f(*(n,)),
        f(*[n]),
        f(n=n),
        f(**{'n': n}),
        apply(f, (n,), {}),
        apply(f, [n], {}),
        f(*(n,), **{}),
        f(*[n], **{}),
        f(n, **{}),
        f(n, *[], **{}),
        f(n=n, **{}),
        f(n=n, *[], **{}),
        f(*(n,), **{}),
        f(*[n], **{}),
        f(*[], **{'n':n}),
        ]
    return r

if __name__ == "__main__":
    print "Break!"
    sleep(0.5)
    #go(f36)
    #go(f38, 100)
    psyco.full()
    try:
        print f35()
        #f23(0.0)
    finally:
        psyco.dumpcodebuf()
