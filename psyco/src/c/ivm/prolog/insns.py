from insnset import InstructionSet


 --- IN-PROGRESS ---


class Immed:
    def __init__(self, *commonvalues):
        self.commonvalues = commonvalues

    def modes(self, ivm):
        for n in self.commonvalues:
            if ivm.nextarg('void', min=n, max=n) is not None:
                return str(n)
        return ivm.nextarg('word_t')

class Address:
    def modes(self, ivm):
        return ivm.nextarg('word_t')

class Stack:
    def modes(self, ivm):
        for i in range(len(ivm.stack)):
            if ivm.nextarg('void', min=i, max=i) is not None:
                return ivm.stack[i]
        n = ivm.nextarg('code_t', min=len(stack), max=255)
        if n is None:
            n = ivm.nextarg('word_t')
        return ivm.compute('stack_nth(%s-%d)' % (n, len(stack)))

class StackRef:
    def modes(self, ivm):
        ...


class IVM(InstructionSet):

    def insn_inv(self):
        x = self.pop(); self.push('~%s' % x)

    def insn_neg_o(self):
        x = self.pop(); self.push('-%s' % x)
        self.setflag('%s == LONG_MIN' % x)

    def insn_abs_o(self):
        x = self.pop(); self.push('%s<0 ? -%s : %s' % (x,x,x))
        self.setflag('%s == LONG_MIN' % x)

    def insn_add(self):
        y = self.pop(); x = self.pop(); self.push('%s+%s' % (x,y))

    def insn_add_o(self):
        y = self.pop(); x = self.pop(); self.push('%s+%s' % (x,y))
        self.setflag('((%s+%s)^%s) < 0 && (%s^%s) >= 0' % (x,y,x,x,y))

    def insn_immed(self, x=Immed(0,1)):
        self.push(x)

    def insn_s_push(self, s=Stack()):
        self.push(s)

    def insn_s_pop(self, s=StackRef()):
        s.write(self.pop())

    def insn_flag_push(self):
        self.push(self.consumeflag())

    def insn_cmpz(self):
        self.pop('x'); self.setflag('x == 0')

    def insn_jumpfar(self, target=Address()):
        self.do('nextip = (code_t*) %s;' % target)
    insn_jumpfar.chainable = False

    def insn_load1(self):
        self.pop('addr'); self.push('*(char*) addr')

    def insn_store1(self):
        self.pop('value'); self.pop('addr')
        self.do('*(char*) addr = value;')


ivm = IVM(['accum'])
ivm.insn_add_o()
ivm.insn_add()
ivm.insn_flag_push()
ivm.normalize(['accum'])
ivm.write()
