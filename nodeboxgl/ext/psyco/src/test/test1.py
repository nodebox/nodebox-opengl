import os
import psyco

def time(fn, *args):
    "Measure the execution time of fn(*args)."
    import time, traceback
    begin = time.clock()
    try:
        result  = fn(*args)
    except:
        end = time.clock()
        traceback.print_exc()
        result = '<exception>'
    else:
        end = time.clock()
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
        if filename[:4] == 'BIN:': 
            f = open(filename[4:], 'rb')
        else:
            f = open(filename, 'r')
        for line in f:
            for c in line:
                k = ord(c)
                result[k] += 1
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
        if filename[:4] == 'BIN:': 
            f = open(filename[4:], 'rb')
        else:
            f = open(filename, 'r')
        for c in f.read():
            k = ord(c)
            result[k] += 1
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
    z = 0j
    for i in xrange(1000):
        z = z*z + c
        if abs(z) > 2:
            if i > 126-33: i = 126-33
            return chr(33+i)
    return " "

def f7(start, end, step):
    "Computes the Mandelbrot set. All args are complex numbers."
    width = int((end.real - start.real) / step.real)
    while start.imag < end.imag:
        line = [mandelbrot(start + n*step.real) for n in range(width)]
        print ''.join(line)
        start += complex(0, step.imag)

def mandelbrotbis(c_r, c_i):
    z_r = z_i = 0.0
    for i in xrange(1000):
        z_r, z_i = z_r*z_r-z_i*z_i + c_r, 2*z_r*z_i + c_i
        if z_r*z_r+z_i*z_i > 4.0:
            if i > 126-33: i = 126-33
            return chr(33+i)
    return " "

def f7bis((start_r, start_i), (end_r, end_i), (step_r, step_i)):
    "Computes the Mandelbrot set. All args are (real, imag) tuples."
    width = int((end_r - start_r) / step_r)
    while start_i < end_i:
        line = [mandelbrotbis(start_r + n*step_r, start_i) for n in range(width)]
        print ''.join(line)
        start_i += step_i

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

def f11(n):
    def subtracter(x, y=n):
        return x-y
    return subtracter(1000)


ALLTESTS = []

def go(f, *args):
    print '-'*78
    v1, t1 = time(psyco.proxy(f), *args)
    print v1
    print '^^^ computed by Psyco in %s seconds' % t1
    v2, t2 = time(f, *args)
    if v1 == v2:
        if t1 and t2:
            ok = '%.2f times faster' % (t2/float(t1))
            s = ', Psyco is %s' % ok
        else:
            ok = s = ''
        print 'Python got the same result in %s seconds%s' % (t2, s)
    else:
        print v2
        print '^^^ by Python in %s seconds' % t2
        print '*'*78
        print '!!! different results !!!'
        ok = 'DIFFERENT RESULTS'
    ALLTESTS.append((f.func_name,t2,t1,ok))

def print_results():
    import sys
    print
    print '='*23, 'Summary (Python %d.%d.%d)' % sys.version_info[:3], '='*23
    format = '%-15s  %-15s  %-15s  %s'
    print format % ('function', 'Python time', 'Psyco time', '')
    for r in ALLTESTS:
        print format % r

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

def go7bis(start=(-2.0, -1.0), end=(1.0, 1.0), step=(0.04, 0.08)):
    go(f7bis, start, end, step)


if __name__ == "__main__":
    go(f11, 50)
    go1()
    go4()
    go5()
    go6()
    go7()
    go7bis()
    go(f10)
    psyco.dumpcodebuf()
    print_results()
