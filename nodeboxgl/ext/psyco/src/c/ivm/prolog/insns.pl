:- consult(vmwriter).
:- consult(mode_combine).


unary_insn(inv).
unary_insn(neg_o, '-').
overflow_flag(neg_o).
unary_insn(abs_o).
overflow_flag(abs_o).

binary_insn(add, '+').
binary_insn(add_o, '+').
overflow_flag(add_o).
binary_insn(sub_o, '-').
overflow_flag(sub_o).
binary_insn(mul_o, '*').
overflow_flag(mul_o).
binary_insn(or).
binary_insn(and).
binary_insn(xor).
%binary_insn(div).
binary_insn(lshift, '<<').
binary_insn(rshift, '>>').
insn(urshift, [], [out(0)=(unsigned(in(1))>>in(0))],    [stack(2->1)]).
insn(cmpeq,  [], [setflag=(in(1)=:=in(0))], [flag(set), stack(2->0)]).
insn(cmplt,  [], [setflag=(in(1) < in(0))], [flag(set), stack(2->0)]).
insn(cmpltu, [], [setflag=(unsigned(in(1)) < unsigned(in(0)))],
                                            [flag(set), stack(2->0)]).

%insn(pop,    [],  [], [stack(pop(0))]).  % note: this is the same as s_pop(0)
%insn(pop2nd, [],  [], [stack(pop(1))]).
insn(settos, [s], [], [stack(settos), nonchainable]).
insn(pushn,  [i], [], [stack(pushn), nonchainable]).

insn(immed, [i([0,1])], [out(0) = arg(0)], [stack(push)]).
insn(s_push,   [s], [out(0) = arg(0)], [stack(push)]).
insn(s_pop,    [s], [arg(0) = in(0)],  [stack(pop)]).
insn(ref_push, [i], [out(0) = addr(stack_nth(arg(0)-stkshft))], [stack(push)]).
insn(stackgrow, [], [impl_stackgrow('VM_EXTRA_STACK_SIZE')], []).

insn(assertdepth, [i], [comment('debugging assertion')], []).
insn(dynamicfreq, [l], [impl_dynamicfreq], [nonchainable]).

insn(flag_push, [], [out(0)=flag],       [stack(push), flag(get)]).
insn(cmpz,      [], [setflag=not(in(0))], [stack(pop), flag(set)]).
insn(flag_forget, [],[], [flag(get), suffixonly]).
insn(jcondnear,[b], [impl_jcond(flag, nextip+arg(0))],[nonchainable,flag(get)]).
insn(jcondfar, [l], [impl_jcond(flag, arg(0))],       [nonchainable,flag(get)]).
insn(jumpfar,  [l], [impl_jump(arg(0))],              [nonchainable]).

insn(cbuild1, [l], [impl_cbuild1(arg(0))], [nonchainable]).
insn(cbuild2, [l], [impl_cbuild2(arg(0), in(0))],
        [stack(1->0), nonchainable]).

unary_insn(load1,  mem1).
unary_insn(load1u, mem1u).
unary_insn(load2,  mem2).
unary_insn(load2u, mem2u).
unary_insn(load4,  mem4).
insn(store1, [], [mem1(in(1)) = cast1(in(0))], [stack(2->0)]).
insn(store2, [], [mem2(in(1)) = cast2(in(0))], [stack(2->0)]).
insn(store4, [], [mem4(in(1)) = in(0)], [stack(2->0)]).

insn(incref,   [],  [impl_incref(in(0))],  [stack(1->0)]).
insn(decref,   [],  [impl_decref(in(0))],  [stack(1->0)]).
insn(decrefnz, [l], [impl_decrefnz(arg(0))], []).

insn(exitframe, [], [impl_exitframe(in(2), in(1), in(0))], [stack(3->0)]).
insn(ret,      [s], [impl_ret(in(0))], [stack(settos), nonchainable]).
insn(retval,    [], [retval=in(0)], [stack(pop)]).
insn(pushretval,[], [out(0)=retval], [stack(push)]).

insn(pyenter,  [l], [impl_pyenter(arg(0))], []).  % enter a Python sub-function
insn(pyleave,  [],  [impl_pyleave], []).          % exit a Python sub-function
insn(vmcall,   [l], [out(0)=impl_vmcall(arg(0)),  % call a Python sub-function
                     impl_stackgrow('VM_INITIAL_MINIMAL_STACK_SIZE')],
                                 [stack(0->1), nonchainable, nostackanalysis]).
% The normal sequence is pyenter/vmcall/pyleave, but vmcall might be
% omitted if the called function is inlined.

insn(ccall0,   [l], [out(0)=impl_ccall(0, arg(0), macro_noarg)],[stack(0->1)]).
insn(CallInsn, [l], [out(0)=impl_ccall(N, arg(0), ArgDef)],     [stack(N->1)]) :-
        between(1, 7, N),
        sformat(SInsn, 'ccall~d', [N]),
        N1 is N-1,
        findall(S, (S=in(M), between(0, N1, M)), Args),
        ArgDef =.. [macro_args | Args],
        string_to_atom(SInsn, CallInsn).

insn(checkdict, [l,l,l,l], [setflag=impl_checkdict(arg(0), arg(1), arg(2),
        arg(3))], [flag(set)]).


% custom operand modes
standard_mode(small, _, i([H|_]), H).
standard_mode(Size,  _, i([_|T]), Value) :- standard_mode(Size, _, i(T), Value).
standard_mode(Size,  _, i([]),    Cond)  :- standard_mode(Size, _, i, Cond).


%mode_combine([s_push(0), immed(char), cmplt, jcondfar(long)]).
%mode_combine([s_push(0), immed(char), add, pop2nd]).
%mode_combine([s_push(truestack(byte)), immed(char), add, pop2nd]).
%
%mode_combine([not, jcondfar(long)]).
%
%mode_combine([immed(long), immed(long), threeway(0)]).
%mode_combine([immed(long), immed(long), threeway(1)]).

%XXX fix duplicate [immed(long), immed(long)]

%mode_combine([s_push(1:255), s_push(2:255)]).
