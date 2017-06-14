from __future__ import generators
import os, sys, random
import psyco


def do_test_1(objects):
    d = [{} for i in range(20)]
    s = [psyco.compact() for i in range(20)]
    attrnames = list('abcdefghijklmnopqrstuvwxyz')
    for j in range(5000):
        i = random.randrange(0, 20)
        attr = random.choice(attrnames)
        if random.randrange(0, 2):
            if attr in d[i]:
                if random.randrange(0,5) == 3:
                    delattr(s[i], attr)
                    del d[i][attr]
                else:
                    assert d[i][attr] == getattr(s[i], attr)
            else:
                try:
                    getattr(s[i], attr)
                except AttributeError:
                    pass
                else:
                    raise AssertionError, attr
        else:
            obj = random.choice(objects)
            setattr(s[i], attr, obj)
            d[i][attr] = obj
    for i in range(20):
        d1 = {}
        for attr in attrnames:
            try:
                d1[attr] = getattr(s[i], attr)
            except AttributeError:
                pass
        assert d[i] == d1

def do_test(n, do_test_1=do_test_1):
    random.jumpahead(n*111222333444555666777L)
    N = 1
    TAIL = 'lo'
    objects = [None, -1, 0, 1, 123455+N, -99-N,
               'hel'+TAIL, [1,2], {(5,): do_test}, 5.43+0.01*N, xrange(5)]
    do_test_1(objects)
    for o in objects[4:]:
        #print '%5d  -> %r' % (sys.getrefcount(o), o)
        assert sys.getrefcount(o) == 4

psyco.cannotcompile(do_test)


def subprocess_test(n):
    sys.stdout.flush()
    childpid = os.fork()
    if not childpid:
        do_test(n)
        sys.exit(0)
    childpid, status = os.wait()
    return os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0

##def test_compact_stress(repeat=20):
##    for i in range(repeat):
##        yield subprocess_test, i

# ____________________________________________________________

def read_x(k):
    return k.x + 1

def read_y(k):
    return k.y

def read_z(k):
    return k.z

psyco.bind(read_x)
psyco.bind(read_y)

def pcompact_test():
    k = psyco.compact()
    k.x = 12
    k.z = None
    k.y = 'hello'
    print read_x(k)
    print read_y(k)
    print read_z(k)
    #psyco.dumpcodebuf()

def pcompact_creat(obj):
    base = sys.getrefcount(obj)
    items = []
    for i in range(11):
        k = psyco.compact()
        k.x = (0,i,i*2)
        k.y = i+1
        k.z = None
        k.t = obj
        k.y = i+2
        k.y = i+3
        print k.x, k.y, k.z, k.t
        items.append(k)
        del k
    print sys.getrefcount(obj) - base
    del items[:]
    print sys.getrefcount(obj) - base

psyco.bind(pcompact_creat)

def pcompact_modif(obj):
    base = sys.getrefcount(obj)
    for i in range(21):
        k = psyco.compact()
        #k.x = i+1
        #k.y = (i*2,i*3,i*4,i*5,i*6,i*7)
        k.x = obj
        print k.x,
        print sys.getrefcount(obj) - base,
        k.x = i+1
        print sys.getrefcount(obj) - base,
        print k.x
        #k.x = len
        #k.x = i+2
        #print k.x, k.y
    print sys.getrefcount(obj) - base

psyco.bind(pcompact_modif)

# ____________________________________________________________

class Rect(psyco.compact):
    def __init__(self, w, h):
        self.w = w
        self.h = h
    def getarea(self):
        return self.w * self.h

def test_rect():
    assert Rect(10, 12).getarea() == 120
    assert Rect(0.5, 2.5).getarea() == 1.25
    assert Rect([1,2,3], 2).getarea() == [1,2,3,1,2,3]

class ClassWithNoInit(psyco.compact):
    pass

def test_init_arguments():
    import py
    def f1(): Rect()
    def f2(): psyco.compact(12)
    def f3(): ClassWithNoInit(21)
    py.test.raises(TypeError, f1)
    if sys.version >= (2, 3):
        py.test.raises(TypeError, f2)
        py.test.raises(TypeError, f3)
    py.test.raises(TypeError, psyco.proxy(f1))
    if sys.version >= (2, 3):
        py.test.raises(TypeError, psyco.proxy(f2))
        py.test.raises(TypeError, psyco.proxy(f3))

def test_special_attributes():
    missing = object()
    r = Rect(6, 7)
    assert r.__members__ == ['w', 'h']
    assert r.__dict__.items() == [('w', 6), ('h', 7)]
    assert r.__dict__ == {'w': 6, 'h': 7}
    assert {'w': 6, 'h': 7} == r.__dict__
    assert list(r.__dict__) == ['w', 'h']
    del r.__dict__['w']
    assert getattr(r, 'w', missing) is missing
    assert r.h == 7
    assert r.__members__ == ['h']
    assert r.__dict__.items() == [('h', 7)]
    assert r.__dict__ == {'h': 7}
    assert {'h': 7} == r.__dict__
    assert list(r.__dict__) == ['h']
    del r.h
    assert r.__members__ == []
    assert getattr(r, 'w', missing) is missing
    assert getattr(r, 'h', missing) is missing

def test_inheritance():
    class X(psyco.compact):
        pass
    class Y(psyco.compact):
        pass
    class Z(X):
        pass
    x = X()
    x.a = 5
    assert [s for s in dir(x) if not s.startswith('__')] == ['a']
    x.__class__ = Y
    assert type(x) is Y
    assert x.__class__ is Y
    assert Y.__bases__ == (psyco.compact,)
    assert Z.__bases__ == (X,)
    if sys.version >= (2,3):   # can't assign to __bases__ in Python 2.2
        Z.__bases__ = (Y,)
        assert Z.__bases__ == (Y,)

psyco.cannotcompile(test_inheritance)  # because of type mutation

def test_data_descr():
    global done
    done = []
    class X(psyco.compact):
        def g(self): done.append('g')
        def s(self, value): done.append(value)
        def d(self): done.append('d')
        a = property(g,s,d)
    x = X()
    x.__dict__['a'] = 'this is hidden'
    r = x.a
    assert r is None
    x.a = 123
    del x.a
    del x.a
    assert done == ['g', 123, 'd', 'd']
    assert x.__dict__ == {'a': 'this is hidden'}
    x.__dict__ = {'a': 'this too'}
    assert x.__dict__ == {'a': 'this too'}
    assert done == ['g', 123, 'd', 'd']

def test_ass_dict():
    missing = object()
    x = psyco.compact()
    x.a = 5
    assert x.__dict__ == {'a': 5}
    x.__dict__ = {'b': 6}
    assert x.b == 6
    assert getattr(x, 'a', missing) is missing
    assert x.__dict__ == {'b': 6}
    y = psyco.compact()
    y.__dict__ = x.__dict__
    assert y.__dict__ == {'b': 6}
    y.__dict__ = y.__dict__
    assert y.__dict__ == {'b': 6}

def test_with_psyco():
    yield psyco.proxy(test_rect)
    yield psyco.proxy(test_special_attributes)
    yield psyco.proxy(test_data_descr)

def test_compact_stress(repeat=20):
    for i in range(repeat):
        yield do_test, i

rect1 = Rect(0, 0)

def test_constant_obj():
    def f1():
        return rect1.w * rect1.h
    def f2(a):
        rect1.w = a
    psyco.bind(f1)
    psyco.bind(f2)
    rect1.w = 6
    rect1.h = 7
    res = f1()
    assert res == 42
    f2(4)
    res = f1()
    assert res == 28
    f2(0.5)
    res = f1()
    assert res == 3.5

# ____________________________________________________________

if __name__ == '__main__':
    import time; print "break!"; time.sleep(1)
    #subprocess_test(10)
    #pcompact_test()
    #pcompact_creat('hel' + 'lo')
    #pcompact_modif('hel' + 'lo')
    #test_constant_obj()
    psyco.proxy(test_rect)()
    #psyco.proxy(test_special_attributes)()
    #psyco.proxy(test_data_descr)()
    psyco.dumpcodebuf()
