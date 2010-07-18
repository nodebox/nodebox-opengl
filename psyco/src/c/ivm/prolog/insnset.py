

class InstructionSet:

    def __init__(self, stack):
        self.locals = {}
        self.stack = stack
        self.popped = 0
        self.flag = 'flag'
        self.codelines = []

    def do(self, code):
        self.codelines.append(code)

    def push(self, expr):
        self.stack.append(expr)

    def compute(self, expr):
        if expr in self.locals:
            return expr
        name = 'l%d' % len(self.locals)
        self.locals[name] = expr
        self.do('%s = %s;' % (name, expr))
        return name

    def pop(self):
        if self.stack:
            name = self.compute(self.stack.pop())
        else:
            name = self.compute('stack_nth(%d);' % self.popped)
            self.popped += 1
        return name

    def setflag(self, expr):
        self.flag = expr

    def forgetflag(self):
        self.flag = None

    def consumeflag(self):
        result = self.flag
        self.forgetflag()
        return result

    def normalize(self, stack):
        rstack = list(stack)
        rstack.reverse()
        code = ['%s = %s;' % (target, self.pop()) for target in rstack]
        shift = self.popped-len(self.stack)
        code += ['stack_nth(%d) = %s;' % (i, self.pop())
                 for i in range(len(self.stack))]
        if self.flag is not None and self.flag != 'flag':
            self.do('flag = %s;' % self.flag)
        if shift != 0:
            if shift > 0:
                self.do('stack_shift_pos(%d);' % shift)
            else:
                self.do('stack_shift(%d);' % shift)
        for line in code:
            self.do(line)
        self.stack = list(stack)
        self.popped = 0

    def write(self):
        print '{'
        if self.locals:
            locals = self.locals.keys()
            locals.sort()
            print '\tword_t %s;' % (', '.join(locals),)
        for line in self.codelines:
            print '\t' + line
        print '}'


class InstructionSetWriter:

    def __init__(self, InsnSet, nbaccum=1):
        self.InsnSet = InsnSet
        self.nbaccum = nbaccum

    
