#! /usr/bin/env python

"""
"PYSTONE" Benchmark Program

Version:        Python/1.1 (corresponds to C/1.1 plus 2 Pystone fixes)

Author:         Reinhold P. Weicker,  CACM Vol 27, No 10, 10/84 pg. 1013.

                Translated from ADA to C by Rick Richardson.
                Every method to preserve ADA-likeness has been used,
                at the expense of C-ness.

                Translated from C to Python by Guido van Rossum.

Version History:

                Version 1.1 corrects two bugs in version 1.0:

                First, it leaked memory: in Proc1(), NextRecord ends
                up having a pointer to itself.  I have corrected this
                by zapping NextRecord.PtrComp at the end of Proc1().

                Second, Proc3() used the operator != to compare a
                record to None.  This is rather inefficient and not
                true to the intention of the original benchmark (where
                a pointer comparison to None is intended; the !=
                operator attempts to find a method __cmp__ to do value
                comparison of the record).  Version 1.1 runs 5-10
                percent faster than version 1.0, so benchmark figures
                of different versions can't be compared directly.

"""

LOOPS = 100000
LOOPS1 = 100000  # number of loops for the first run of Psyco

from time import clock

__version__ = "1.1"

[Ident1, Ident2, Ident3, Ident4, Ident5] = range(1, 6)

class Record:

    def __init__(self, PtrComp = None, Discr = 0, EnumComp = 0,
                       IntComp = 0, StringComp = 0):
        self.PtrComp = PtrComp
        self.Discr = Discr
        self.EnumComp = EnumComp
        self.IntComp = IntComp
        self.StringComp = StringComp

    def copy(self):
        return Record(self.PtrComp, self.Discr, self.EnumComp,
                      self.IntComp, self.StringComp)

TRUE = 1
FALSE = 0

def mydiv(a,b):
    try:
        return float(a) / b
    except:
        return float("nan")

def main():
    print "Pystone(%s)                   time     loops per second" % __version__
    py_time, = pystones_reg(LOOPS1+LOOPS)
    pyloop_time = py_time / (LOOPS1+LOOPS)
    print "regular Python for %d passes  %g        %g" % \
          (LOOPS1+LOOPS, py_time, mydiv(1, pyloop_time))
    psy_time1, psy_time = pystones_psycho(LOOPS1, LOOPS)
    print "Psyco for %d passes           %g        %g" % \
          (LOOPS1, psy_time1, mydiv(LOOPS1, psy_time1))
    print "Psyco for %d more passes      %g        %g" % \
          (LOOPS, psy_time, mydiv(LOOPS, psy_time))
    print "Total for %d passes           %g        %g" % \
          (LOOPS1+LOOPS, psy_time1+psy_time, 
             mydiv(LOOPS1+LOOPS, psy_time1+psy_time))

    # invert the equation system:
    #   psy_time1          = start_time + LOOPS1*loop_time
    #   psy_time1+psy_time = start_time + (LOOPS1+LOOPS)*loop_time
    loop_time = psy_time/LOOPS
    start_time = psy_time1 - LOOPS1*loop_time
    print "Separated compilation/execution timings for %d passes" % \
          (LOOPS1+LOOPS)
    print "Compilation (i.e. start-up)   %g        %g" % \
          (start_time, mydiv(1, start_time))
    print "Machine code execution        %g        %g" % \
          (loop_time*(LOOPS1+LOOPS), mydiv(1, loop_time))
    print
    print "Relative execution frequencies (iterations per second)"
    print "iterations        Psyco        Python    Psyco is ... times faster"
    for d in range(8):
        n = 10**d
        psyco1 = mydiv(n, start_time+n*loop_time)
        print " %8d       %g         %g           %.2f" % \
            (n, psyco1, mydiv(1, pyloop_time), psyco1*pyloop_time)

    # invert the equation
    #   start_time + c*loop_time = c*pyloop_time
    if pyloop_time <= loop_time:
        print "Psyco is always slower than regular Python."
    else:
        c = mydiv(start_time, pyloop_time - loop_time)
        print "Cut-off point: %.1f iterations" % c
    if start_time < 0.07:
        print "Note: start-up time is very low, the above figure is not reliable."
        print "You should consider running the same benchmark a large number of times"
        print "and taking the mean value for the cut-off point."

def pystones_psycho(*loopslist):
    import psyco
    #old_dict = Record.__dict__.copy()
    #try:
        # replace all methods of Record by proxies
        #for key, value in old_dict.items():
        #    if type(value) is type(main):
        #        Record.__dict__[key] = _psyco.proxy(value, 99)
    f = psyco.proxy(Proc0)
    return map(f, loopslist)
    #finally:
    #    Record.__dict__.update(old_dict)

def pystones_reg(*loopslist):
    return map(Proc0, loopslist)

IntGlob = 0
BoolGlob = FALSE
Char1Glob = '\0'
Char2Glob = '\0'
Array1Glob = [0]*51
Array2Glob = map(lambda x: x[:], [Array1Glob]*51)
PtrGlb = None
PtrGlbNext = None

def Proc0(loops=LOOPS):
    global IntGlob
    global BoolGlob
    global Char1Glob
    global Char2Glob
    global Array1Glob
    global Array2Glob
    global PtrGlb
    global PtrGlbNext

    PtrGlbNext = Record()
    PtrGlb = Record()
    PtrGlb.PtrComp = PtrGlbNext
    PtrGlb.Discr = Ident1
    PtrGlb.EnumComp = Ident3
    PtrGlb.IntComp = 40
    PtrGlb.StringComp = "DHRYSTONE PROGRAM, SOME STRING"
    String1Loc = "DHRYSTONE PROGRAM, 1'ST STRING"
    Array2Glob[8][7] = 10

    starttime = clock()

    for i in range(loops):
        Proc5()
        Proc4()
        IntLoc1 = 2
        IntLoc2 = 3
        String2Loc = "DHRYSTONE PROGRAM, 2'ND STRING"
        EnumLoc = Ident2
        BoolGlob = not Func2(String1Loc, String2Loc)
        while IntLoc1 < IntLoc2:
            IntLoc3 = 5 * IntLoc1 - IntLoc2
            IntLoc3 = Proc7(IntLoc1, IntLoc2)
            IntLoc1 = IntLoc1 + 1
        Proc8(Array1Glob, Array2Glob, IntLoc1, IntLoc3)
        PtrGlb = Proc1(PtrGlb)
        CharIndex = 'A'
        while CharIndex <= Char2Glob:
            if EnumLoc == Func1(CharIndex, 'C'):
                EnumLoc = Proc6(Ident1)
            CharIndex = chr(ord(CharIndex)+1)
        IntLoc3 = IntLoc2 * IntLoc1
        IntLoc2 = IntLoc3 / IntLoc1
        IntLoc2 = 7 * (IntLoc3 - IntLoc2) - IntLoc1
        IntLoc1 = Proc2(IntLoc1)

    benchtime = clock() - starttime
    return benchtime

def Proc1(PtrParIn):
    PtrParIn.PtrComp = NextRecord = PtrGlb.copy()
    PtrParIn.IntComp = 5
    NextRecord.IntComp = PtrParIn.IntComp
    NextRecord.PtrComp = PtrParIn.PtrComp
    NextRecord.PtrComp = Proc3(NextRecord.PtrComp)
    if NextRecord.Discr == Ident1:
        NextRecord.IntComp = 6
        NextRecord.EnumComp = Proc6(PtrParIn.EnumComp)
        NextRecord.PtrComp = PtrGlb.PtrComp
        NextRecord.IntComp = Proc7(NextRecord.IntComp, 10)
    else:
        PtrParIn = NextRecord.copy()
    NextRecord.PtrComp = None
    return PtrParIn

def Proc2(IntParIO):
    IntLoc = IntParIO + 10
    while 1:
        if Char1Glob == 'A':
            IntLoc = IntLoc - 1
            IntParIO = IntLoc - IntGlob
            EnumLoc = Ident1
        if EnumLoc == Ident1:
            break
    return IntParIO

def Proc3(PtrParOut):
    global IntGlob

    if PtrGlb is not None:
        PtrParOut = PtrGlb.PtrComp
    else:
        IntGlob = 100
    PtrGlb.IntComp = Proc7(10, IntGlob)
    return PtrParOut

def Proc4():
    global Char2Glob

    BoolLoc = Char1Glob == 'A'
    BoolLoc = BoolLoc or BoolGlob
    Char2Glob = 'B'

def Proc5():
    global Char1Glob
    global BoolGlob

    Char1Glob = 'A'
    BoolGlob = FALSE

def Proc6(EnumParIn):
    EnumParOut = EnumParIn
    if not Func3(EnumParIn):
        EnumParOut = Ident4
    if EnumParIn == Ident1:
        EnumParOut = Ident1
    elif EnumParIn == Ident2:
        if IntGlob > 100:
            EnumParOut = Ident1
        else:
            EnumParOut = Ident4
    elif EnumParIn == Ident3:
        EnumParOut = Ident2
    elif EnumParIn == Ident4:
        pass
    elif EnumParIn == Ident5:
        EnumParOut = Ident3
    return EnumParOut

def Proc7(IntParI1, IntParI2):
    IntLoc = IntParI1 + 2
    IntParOut = IntParI2 + IntLoc
    return IntParOut

def Proc8(Array1Par, Array2Par, IntParI1, IntParI2):
    global IntGlob

    IntLoc = IntParI1 + 5
    Array1Par[IntLoc] = IntParI2
    Array1Par[IntLoc+1] = Array1Par[IntLoc]
    Array1Par[IntLoc+30] = IntLoc
    for IntIndex in range(IntLoc, IntLoc+2):
        Array2Par[IntLoc][IntIndex] = IntLoc
    Array2Par[IntLoc][IntLoc-1] = Array2Par[IntLoc][IntLoc-1] + 1
    Array2Par[IntLoc+20][IntLoc] = Array1Par[IntLoc]
    IntGlob = 5

def Func1(CharPar1, CharPar2):
    CharLoc1 = CharPar1
    CharLoc2 = CharLoc1
    if CharLoc2 != CharPar2:
        return Ident1
    else:
        return Ident2

def Func2(StrParI1, StrParI2):
    IntLoc = 1
    while IntLoc <= 1:
        if Func1(StrParI1[IntLoc], StrParI2[IntLoc+1]) == Ident1:
            CharLoc = 'A'
            IntLoc = IntLoc + 1
    if CharLoc >= 'W' and CharLoc <= 'Z':
        IntLoc = 7
    if CharLoc == 'X':
        return TRUE
    else:
        if StrParI1 > StrParI2:
            IntLoc = IntLoc + 7
            return TRUE
        else:
            return FALSE

def Func3(EnumParIn):
    EnumLoc = EnumParIn
    if EnumLoc == Ident3: return TRUE
    return FALSE

if __name__ == '__main__':
    main()
