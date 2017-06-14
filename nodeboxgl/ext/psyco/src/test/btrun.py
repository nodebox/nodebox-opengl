
##### Prelude #####

>>> import sys, uu, psyco
>>> psyco.full()
>>> import test1, test3, test5
>>> import test_compactobject as compactobject

>>> def prep():
...     uu.decode('file2-basetests.uu', 'file2-basetests')

>>> def g1(f):
...     prep()
...     d = f(['file1-basetests', 'BIN:file2-basetests'])
...     return [d[chr(n)] for n in range(256)]

>>> def protect(f, *args):
...     try:
...         return f(*args)
...     except:
...         return 'exception: ' + sys.exc_info()[0].__name__

>>> def assert_true(cond):
...     if cond:
...         print 'Ok'
...     else:
...         print 'Assert failed!'

>>> True,False = 1==1,1==0

>>> PY21 = sys.hexversion < 0x02020000

>>> if sys.hexversion >= 0x02040000:
...     def clamp(x):
...         return x
... else:
...     def clamp(x):
...         if x & (sys.maxint+1L):
...             return int(x & sys.maxint) - sys.maxint - 1
...         else:
...             return int(x & sys.maxint)

                             ###################
                             ####   TEST1   ####
                             ###################

>>> print test1.f1(217)
1115467

>>> print test1.f2(0)
0

>>> print test1.f2(-192570368)
-385140736

>>> test1.f3([3,4,0,'testing',12.75,(5,3,1),0])
6
8
testingtesting
25.5
(5, 3, 1, 5, 3, 1)

>>> print g1(test1.f5)
[20, 14, 19, 9, 12, 25, 13, 9, 17, 23, 289, 26, 15, 13, 17, 19, 23, 18, 15, 14, 18, 22, 14, 18, 18, 17, 21, 27, 21, 20, 15, 12, 1745, 18, 17, 136, 25, 14, 27, 18, 92, 87, 386, 12, 52, 29, 63, 102, 49, 39, 26, 26, 18, 14, 16, 13, 22, 16, 29, 49, 24, 34, 30, 20, 16, 100, 98, 61, 20, 85, 61, 75, 54, 49, 19, 47, 32, 18, 67, 47, 86, 66, 184, 61, 42, 42, 74, 14, 26, 55, 74, 16, 37, 15, 19, 211, 17, 348, 369, 130, 12, 248, 264, 328, 162, 68, 69, 41, 128, 29, 240, 95, 244, 288, 673, 295, 108, 134, 380, 40, 42, 224, 137, 30, 15, 24, 11, 15, 6, 15, 19, 26, 19, 17, 15, 18, 16, 17, 11, 14, 11, 15, 11, 11, 19, 13, 18, 25, 14, 20, 12, 14, 8, 13, 17, 15, 16, 17, 15, 13, 12, 12, 10, 19, 15, 15, 16, 12, 24, 21, 14, 10, 19, 17, 14, 13, 20, 18, 11, 17, 21, 13, 21, 19, 17, 15, 19, 10, 17, 12, 16, 13, 16, 15, 13, 16, 16, 16, 15, 14, 11, 14, 18, 15, 25, 9, 19, 12, 13, 12, 18, 12, 13, 16, 13, 17, 18, 19, 16, 11, 18, 18, 27, 11, 22, 17, 13, 22, 20, 16, 9, 17, 14, 12, 20, 17, 15, 18, 16, 15, 15, 16, 16, 18, 18, 17, 21, 17, 12, 12, 17, 10, 20, 19, 18, 25]

>>> assert_true(PY21 or g1(test1.f4) == g1(test1.f5))
Ok

>>> print test1.f6(n=100, p=10001)
803

>>> test1.f7(-2-1j, 1+1j, 0.04+0.08j)
!!!!!!!""""""####################$$$$$$$$%%%&'*.)+ %$$$$$######""""""""""""
!!!!!!"""""####################$$$$$$$$%%%%&'(+2-)'&%%$$$$$######""""""""""
!!!!!""""###################$$$$$$$$$%%%&&'6E0~ 9=6(&%%%%$$$$######""""""""
!!!!"""###################$$$$$$$$%%&&&&''(+B     @('&&%%%%%$$#######""""""
!!!"""##################$$$$$$$%%&(,32)),5+,/M   E-,*+)''''-&$$#######"""""
!!!"#################$$$$$%%%%%&&&(,b~~/:             0,,:/;/&%$########"""
!!"###############$$$%%%%%%%%&&&&()+/?                     ='&%$$########""
!!"###########$$$%'&&&&%%%&&&&'')U ~                      G,('%%$$#######""
!"######$$$$$$%%&&*+)(((2*(''(()2p                         :@:'%$$########"
!###$$$$$$$$%%%%&'(*.IB24 0J,**+~                           -(&%$$$########
!#$$$$$$$$%%%%%&'',+2~        //                            ?*&%$$$########
!$$$$$$$%&&&&'(I+,-j           9                           ~*&%%$$$########
!%%&&')''((()-+/S                                          ('&%%$$$$#######
!%%&&')''((()-+/S                                          ('&%%$$$$#######
!$$$$$$$%&&&&'(I+,-j           9                           ~*&%%$$$########
!#$$$$$$$$%%%%%&'',+2~        //                            ?*&%$$$########
!###$$$$$$$$%%%%&'(*.IB24 0J,**+~                           -(&%$$$########
!"######$$$$$$%%&&*+)(((2*(''(()2p                         :@:'%$$########"
!!"###########$$$%'&&&&%%%&&&&'')U ~                      G,('%%$$#######""
!!"###############$$$%%%%%%%%&&&&()+/?                     ='&%$$########""
!!!"#################$$$$$%%%%%&&&(,b~~/:             0,,:/;/&%$########"""
!!!"""##################$$$$$$$%%&(,32)),5+,/M   E-,*+)''''-&$$#######"""""
!!!!"""###################$$$$$$$$%%&&&&''(+B     @('&&%%%%%$$#######""""""
!!!!!""""###################$$$$$$$$$%%%&&'6E0~ 9=6(&%%%%$$$$######""""""""
!!!!!!"""""####################$$$$$$$$%%%%&'(+2-)'&%%$$$$$######""""""""""
!!!!!!!""""""####################$$$$$$$$%%%&'*.)+J%$$$$$######""""""""""""

>>> test1.f7bis((-2.0, -1.0), (1.0, 1.0), (0.04, 0.08))
!!!!!!!""""""####################$$$$$$$$%%%&'*.)+ %$$$$$######""""""""""""
!!!!!!"""""####################$$$$$$$$%%%%&'(+2-)'&%%$$$$$######""""""""""
!!!!!""""###################$$$$$$$$$%%%&&'6E0~ 9=6(&%%%%$$$$######""""""""
!!!!"""###################$$$$$$$$%%&&&&''(+B     @('&&%%%%%$$#######""""""
!!!"""##################$$$$$$$%%&(,32)),5+,/M   E-,*+)''''-&$$#######"""""
!!!"#################$$$$$%%%%%&&&(,b~~/:             0,,:/;/&%$########"""
!!"###############$$$%%%%%%%%&&&&()+/?                     ='&%$$########""
!!"###########$$$%'&&&&%%%&&&&'')U ~                      G,('%%$$#######""
!"######$$$$$$%%&&*+)(((2*(''(()2p                         :@:'%$$########"
!###$$$$$$$$%%%%&'(*.IB24 0J,**+~                           -(&%$$$########
!#$$$$$$$$%%%%%&'',+2~        //                            ?*&%$$$########
!$$$$$$$%&&&&'(I+,-j           9                           ~*&%%$$$########
!%%&&')''((()-+/S                                          ('&%%$$$$#######
!%%&&')''((()-+/S                                          ('&%%$$$$#######
!$$$$$$$%&&&&'(I+,-j           9                           ~*&%%$$$########
!#$$$$$$$$%%%%%&'',+2~        //                            ?*&%$$$########
!###$$$$$$$$%%%%&'(*.IB24 0J,**+~                           -(&%$$$########
!"######$$$$$$%%&&*+)(((2*(''(()2p                         :@:'%$$########"
!!"###########$$$%'&&&&%%%&&&&'')U ~                      G,('%%$$#######""
!!"###############$$$%%%%%%%%&&&&()+/?                     ='&%$$########""
!!!"#################$$$$$%%%%%&&&(,b~~/:             0,,:/;/&%$########"""
!!!"""##################$$$$$$$%%&(,32)),5+,/M   E-,*+)''''-&$$#######"""""
!!!!"""###################$$$$$$$$%%&&&&''(+B     @('&&%%%%%$$#######""""""
!!!!!""""###################$$$$$$$$$%%%&&'6E0~ 9=6(&%%%%$$$$######""""""""
!!!!!!"""""####################$$$$$$$$%%%%&'(+2-)'&%%$$$$$######""""""""""
!!!!!!!""""""####################$$$$$$$$%%%&'*.)+J%$$$$$######""""""""""""

>>> print protect(test1.f8)
in finally clause
exception: ZeroDivisionError

>>> test1.f9(50)
0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49

>>> test1.f10()
0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49

>>> print test1.f11(50)
950

>>> print test1.f11(-1.0)
1001.0

                             ###################
                             ####   TEST2   ####
                             ###################

>>> def f1():
...     return -abs(-10)
>>> print f1()
-10

>>> def f11():
...     return -abs(-10.125)+5.0+6.0
>>> print f11()
0.875

                             ###################
                             ####   TEST3   ####
                             ###################

>>> test3.f11([5,6,7,5,3,5,6,2,5,5,6,7,5])
[0, 0, 0, 1, 0, 1, 2, 0, 1, 1, 2, 3, 4]

>>> print test3.f13((None, 'hello'))
None hello
None hello
('hello', None)

>>> print test3.f13([12, 34])
12 34
12 34
(34, 12)

>>> test3.f14(5)
${True}

>>> test3.f14(-2)
${False}

>>> print test3.f16(123)
-124

>>> print test3.f17('abc')
('abc', 0, ())

>>> print test3.f17('abc', 'def', 'ghi', 'jkl')
('abc', 'def', ('ghi', 'jkl'))

>>> print test3.f19([1,2,3,4])
hello
${([1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4], True, 0)}

>>> print test3.f20('l', 12)
[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110]
>>> print test3.f20('L', 12)
[0L, 10L, 20L, 30L, 40L, 50L, 60L, 70L, 80L, 90L, 100L, 110L]
>>> print test3.f20('i', 12)
[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110]
>>> print test3.f20('I', 12)
[0L, 10L, 20L, 30L, 40L, 50L, 60L, 70L, 80L, 90L, 100L, 110L]
>>> print test3.f20('c', 12, 'x')
['\x00', '\n', '\x14', '\x1e', '(', '2', '<', 'F', 'P', 'Z', 'd', 'n']
>>> print test3.f20('b', 12)
[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110]
>>> print test3.f20('B', 12)
[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110]
>>> print test3.f20('h', 12)
[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110]
>>> print test3.f20('H', 12)
[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110]
>>> print test3.f20('B', 17)
[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]
>>> print test3.f20('h', 28)
[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220, 230, 240, 250, 260, 270]

>>> print test3.f21([2,6,'never',9,3,0.123])
3

>>> test3.f22(0)
Catch!

>>> print test3.f22(-2.0)
None

>>> test3.f23(0.0)
Catch!
Catch!
NameError

>>> test3.f23(23)
NameError

>>> print [x.__name__ for x in test3.f26()]
['float', 'list', 'urllib', 'psyco.classes', 'full']

>>> test3.N=5; print test3.f28(), test3.f28_1(), test3.f28_b(), test3.f28_b1()
test_getframe():
test_getframe
f28
?
5 test_getframe():
test_getframe
test_getframe1
f28_1
?
5 test_getframe_b():
test_getframe_b
f28_b
?
5 test_getframe_b():
test_getframe_b
test_getframe_b1
f28_b1
?
5

>>> print test3.f27(), test3.f27_1(), test3.f27_b(), test3.f27_b1()
test_getframe():
test_getframe
f28
f27
?
test_getframe():
test_getframe
f28
f27
?
test_getframe():
test_getframe
f28
f27
?
(5, 6, 7) test_getframe():
test_getframe
test_getframe1
f28_1
f27_1
?
test_getframe():
test_getframe
test_getframe1
f28_1
f27_1
?
test_getframe():
test_getframe
test_getframe1
f28_1
f27_1
?
(51, 61, 71) test_getframe_b():
test_getframe_b
f28_b
f27_b
?
test_getframe_b():
test_getframe_b
f28_b
f27_b
?
test_getframe_b():
test_getframe_b
f28_b
f27_b
?
(95, 96, 97) test_getframe_b():
test_getframe_b
test_getframe_b1
f28_b1
f27_b1
?
test_getframe_b():
test_getframe_b
test_getframe_b1
f28_b1
f27_b1
?
test_getframe_b():
test_getframe_b
test_getframe_b1
f28_b1
f27_b1
?
(951, 961, 971)

>>> print test3.f29(range(10,0,-1))
[10, 9, 7, 6, 5, 4, 3, 2, 1]

>>> print test3.f32('c:/temp')
('c:', '/temp')
>>> print test3.f32('*')
('', '*')
>>> print test3.f32('/dev/null')
('', '/dev/null')

>>> test3.f33(31)
31
>>> print test3.f33(33)
None
>>> print test3.f33(32)
None

>>> test3.f34(70000)
0
1
3
7
15
31
63
127
255
511
1023
2047
4095
8191
16383
32767
65535

>>> test3.f35()
[[5 5 5]
 [5 5 5]
 [5 5 5]]

>>> test3.f37(None)
${True}
1

>>> print test3.f38(12)
[234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234]

                             ###################
                             ####   TEST5   ####
                             ###################

>>> print hash(test5.f('file1-basetests'))
33961417
>>> prep(); print hash(test5.f('file2-basetests', 'rb'))
2034921519

>>> print test5.f2(4,5,6)
(6, 5, 4)
>>> print test5.f2(4,5,(6,))
(6, 5, 4)

>>> assert_true(test5.f3(15, 32) == (clamp(64424509440L), 30,
...                                  clamp(32212254720L), 0, 7, 0))
Ok
>>> assert_true(test5.f3(15, 31) == (clamp(32212254720L), 30,
...                                  clamp(32212254720L), 0, 7, 0))
Ok
>>> assert_true(test5.f3(15, 33) == (clamp(128849018880L), 30,
...                                  clamp(32212254720L), 0, 7, 0))
Ok
>>> assert_true(test5.f3(15, 63) == (clamp(138350580552821637120L), 30,
...                                  clamp(32212254720L), 0, 7, 0))
Ok
>>> assert_true(test5.f3(-15, 63) == (clamp(-138350580552821637120L), -30,
...                                   clamp(-32212254720L), -1, -8, -1))
Ok
>>> assert_true(test5.f3(-15, 32) == (clamp(-64424509440L), -30,
...                                   clamp(-32212254720L), -1, -8, -1))
Ok
>>> assert_true(test5.f3(-15, 31) == (clamp(-32212254720L), -30,
...                                   clamp(-32212254720L), -1, -8, -1))
Ok
>>> assert_true(test5.f3(-15, 33) == (clamp(-128849018880L), -30,
...                                   clamp(-32212254720L), -1, -8, -1))
Ok
>>> assert_true(test5.f3(-15, 2) == (-60, -30,
...                                  clamp(-32212254720L), -4, -8, -1))
Ok
>>> assert_true(test5.f3(-15, 1) == (-30, -30,
...                                  clamp(-32212254720L), -8, -8, -1))
Ok
>>> assert_true(test5.f3(-15, 0) == (-15, -30,
...                                  clamp(-32212254720L), -15, -8, -1))
Ok
>>> assert_true(test5.f3(15, 0) == (15, 30,
...                                 clamp(32212254720L), 15, 7, 0))
Ok
>>> assert_true(test5.f3(15, 1) == (30, 30,
...                                 clamp(32212254720L), 7, 7, 0))
Ok
>>> assert_true(test5.f3(15, 2) == (60, 30,
...                                 clamp(32212254720L), 3, 7, 0))
Ok
>>> assert_true(test5.f3(-1, 0) == (-1, -2, -2147483648L, -1, -1, -1))
Ok

>>> print test5.f4("some-string")
abcsome-string

>>> print test5.overflowtest()
-3851407362L

>>> test5.booltest()
${False}
${True}
${False}
${True}
${False}
${True}
${[a & b for a in (False,True) for b in (False,True)]}
${[a | b for a in (False,True) for b in (False,True)]}
${[a ^ b for a in (False,True) for b in (False,True)]}
${True}

>>> test5.exc_test()
IndexError list index out of range
2

>>> test5.seqrepeat()
'abcabcabcabcabc'
'abcabcabcabcabc'
[3, 'z', 3, 'z', 3, 'z', 3, 'z', 3, 'z']
[6, 3, 6, 3, 6, 3, 6, 3, 6, 3]
'yyyyyx'
'abcabcabcabcabcabc'
'abcabcabcabcabcabc'
[3, 'z', 3, 'z', 3, 'z', 3, 'z', 3, 'z', 3, 'z']
[6, 3, 6, 3, 6, 3, 6, 3, 6, 3, 6, 3]
'yyyyyyx'
''
''
[]
[]
'x'

>>> test5.f5(99)
100
100
4
100

>>> test5.f5(-3.0)
-2.0
-2.0
4
-2.0

>>> test5.f6(3)
None
None
None
None
5

>>> test5.f6(-2)
-1
-1
None
-1
48

>>> test5.f6(99)
100
100
None
100
IndexError

>>> test5.f6("error")
TypeError

>>> test5.f7(8)
[8, 75, 121]
[8, 15, 11]

>>> test5.f7(8.5)
[8.5, 75, 121]
[8.5, 15, 11]

>>> test5.f8(8)
[0, 30, 44]
[0.0, 0.0, 0.0]

>>> test5.f8(8.5)
[0.0, 30, 44]
[0.0, 0.0, 0.0]

>>> print test5.f9(10)
(4, 11)

>>> assert_true(PY21 or test5.f9(sys.maxint) == (4, 2147483648L))
Ok

>>> test5.teststrings()
'userhruuiadsfz1if623opadoa8ua09q34rx093q\x00qw09exdqw0e9dqw9e8d8qw9r8qw\x1d\xd7\xae\xa2\x06\x10\x1a\x00a\xff\xf6\xee\x15\xa2\xea\x89akjsdfhqweirewru 3498cr 3849rx398du389du389dur398d31623'
'someanother'
'userhru.'
'.userhru'
'userhruuiadsfz'
'akjsdfhqweirewru 3498cr 3849rx398du389du389dur398d31623\x1d\xd7\xae\xa2\x06\x10\x1a\x00a\xff\xf6\xee\x15\xa2\xea\x89qw09exdqw0e9dqw9e8d8qw9r8qw\x0009q34rx093qoa8uaopad623if1uiadsfzuserhru'
1
'a'
'sdfhqweirewru 3498cr 3849rx398du389du389dur398d3'
1
1
0
1

>>> test5.testslices('hello')
''
'hello'
'hello'
''
'hello'
'hello'
''
'ello'
'ello'
''
''
''

>>> test5.testovf(1987654321, 2012345789)
4000000110
4012345789
3987654321
-24691468
-12345789
-12345679
3999847802852004269
4024691578000000000
3975308642000000000
1987654321
-1987654321
1987654321

>>> test5.testovf(-2147483647-1, 2012345789)
-135137859
4012345789
-147483648
-4159829437
-12345789
-4147483648
-4321479675999158272
4024691578000000000
-4294967296000000000
-2147483648
2147483648
2147483648

>>> test5.testovf(-2147483647-1, -2147483647-1)
-4294967296
-147483648
-147483648
0
4147483648
-4147483648
4611686018427387904
-4294967296000000000
-4294967296000000000
-2147483648
2147483648
2147483648

>>> test5.rangetypetest(12)
list
list
list
xrange
xrange
xrange

>>> test5.rangetest(15)
0 1 2 3 4 5 6 7 8 9 10 11 12 13 14
10 11 12 13 14
15 14 13 12 11

>>> test5.xrangetest(15)
0 1 2 3 4 5 6 7 8 9 10 11 12 13 14
10 11 12 13 14
15 14 13 12 11

>>> test5.longrangetest()
[1234567890123456789L, 1234567890123456790L]

>>> print list(xrange(10))
[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

>>> x = xrange(10); print sys.getrefcount(x); print list(x)
2
[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

>>> print list(xrange(-2, 5))
[-2, -1, 0, 1, 2, 3, 4]

>>> print list(xrange(-2, 5, 2))
[-2, 0, 2, 4]

>>> print list(xrange(-2, 5, -2))
[]

>>> print list(xrange(5, -2, -2))
[5, 3, 1, -1]

>>> test5.arraytest()
S

>>> test5.proxy_defargs()
12

>>> test5.setfilter()
('f1', 1)
('f2', 0)

>>> test5.makeSelection()
do stuff here

>>> test5.class_creation_1(1111)
ok

>>> test5.class_creation_2(1111)
ok

>>> test5.class_creation_3()
ok

>>> test5.class_creation_4(1111)
ok

>>> test5.power_int(1)
332833500

>>> test5.power_int(10)
332833500

>>> test5.power_int_long(1)
long 332833500

>>> test5.power_int_long(10)
long 332833500

>>> test5.power_float(1)
float 7038164

>>> test5.power_float(10)
float 7038164

>>> test5.conditional_doubletest_fold()
ok(1)
ok(2)

>>> test5.importname(['ab', 'cd', 'ef'])
Ok

>>> test5.sharedlists(3); test5.sharedlists(12)
4
8

>>> test5.variousslices()
slice(4, None, None)
slice(None, 7, None)
slice(9, 'hello', None)
slice('world', None, None)
slice(1, 10, 'hello')
4 2147483647
0 7
slice(9, 'hello', None)
slice('world', None, None)
slice(1, 10, 'hello')

>>> test5.listgetitem()
foobar
Ok

>>> test5.negintpow(8)
0.015625

                         ###########################
                         ####   COMPACTOBJECT   ####
                         ###########################

>>> for i in range(5): print compactobject.do_test(i) or i
0
1
2
3
4

>>> for i in range(5, 10):
...     compactobject.do_test(i,
...         do_test_1=psyco.proxy(compactobject.do_test_1))
...     print i
5
6
7
8
9

>>> compactobject.pcompact_test()
13
hello
None

>>> compactobject.pcompact_creat('hel' + 'lo')
(0, 0, 0) 3 None hello
(0, 1, 2) 4 None hello
(0, 2, 4) 5 None hello
(0, 3, 6) 6 None hello
(0, 4, 8) 7 None hello
(0, 5, 10) 8 None hello
(0, 6, 12) 9 None hello
(0, 7, 14) 10 None hello
(0, 8, 16) 11 None hello
(0, 9, 18) 12 None hello
(0, 10, 20) 13 None hello
11
0

>>> compactobject.pcompact_modif('hel' + 'lo')
hello 1 0 1
hello 1 0 2
hello 1 0 3
hello 1 0 4
hello 1 0 5
hello 1 0 6
hello 1 0 7
hello 1 0 8
hello 1 0 9
hello 1 0 10
hello 1 0 11
hello 1 0 12
hello 1 0 13
hello 1 0 14
hello 1 0 15
hello 1 0 16
hello 1 0 17
hello 1 0 18
hello 1 0 19
hello 1 0 20
hello 1 0 21
0
