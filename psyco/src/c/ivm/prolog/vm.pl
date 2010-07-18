:- consult(ccode).
:- consult(utils).

:- multifile     insn/4, overflow_flag/1.
:- discontiguous insn/4, overflow_flag/1.
:- multifile     unary_insn/2, binary_insn/2, unary_insn/1, binary_insn/1.
:- discontiguous unary_insn/2, binary_insn/2, unary_insn/1, binary_insn/1.
:- multifile     mode_combine/1, standard_mode/4.


% conditions
condition_range(char,     -128:127).
condition_range(positive, 0:maxint).
condition_range(byte,     0:255).
%condition_range(truestack(byte), A:B) :- initial_stack_depth(A), B = 255.
%condition_range(truestack(long), A:B) :- initial_stack_depth(A), B = maxint.
condition_range(int,      minint:maxint).
condition_range(long,     minint:maxint).
condition_range(minint:maxint, minint:maxint) :- !.
condition_range(minint:B,      minint:Bx    ) :- !, Bx is B.
condition_range(A     :maxint, Ax    :maxint) :- !, Ax is A.
condition_range(A     :B,      Ax    :Bx    ) :- !, Ax is A, Bx is B.
condition_range((C1, C2), A:B) :-
        condition_range(C1, A1:B1),
        condition_range(C2, A2:B2),
        mmax(A1, A2, A),
        mmin(B1, B2, B).
condition_range(C1+Offset, A:B) :-
        condition_range(C1, A1:B1),
        mplus(A1, Offset, A),
        mplus(B1, Offset, B).
condition_range(C1-Offset, A:B) :-
        condition_range(C1, A1:B1),
        mplus(A, Offset, A1),
        mplus(B, Offset, B1).
condition_range(A, A:A) :-
        integer(A).

goal_condition(Cond, V, unsigned(V) =< B) :-
        condition_range(Cond, 0:B),
        integer(B), B>0, !.
goal_condition(Cond, V, V =:= A) :-
        condition_range(Cond, A:A),
        integer(A), !.
goal_condition(Cond, V, G) :-
        condition_range(Cond, A:B),
        goal_in_range(V, A, B, G), !.
goal_condition(indirect(_), _, true).

goal_conj(_, fail, fail) :- !.
goal_conj(fail, _, fail) :- !.
goal_conj(G1, true, G1) :- !.
goal_conj(true, G2, G2) :- !.
goal_conj(G1, G2, (G1, G2)).

goal_leq(A, A, true) :- !.
goal_leq(minint, _, true) :- !.
goal_leq(maxint, _, fail) :- !.
goal_leq(_, maxint, true) :- !.
goal_leq(_, minint, fail) :- !.
goal_leq(A, B, A =< B).

goal_add(0, A, A) :- !.
goal_add(A, 0, A) :- !.
goal_add(A, B, B+A).

mmin(A, B, A) :- goal_leq(A, B, G), G, !.
mmin(_, B, B).
mmax(A, B, B) :- goal_leq(A, B, G), G, !.
mmax(A, _, A).
mplus(minint, _, minint).
mplus(maxint, _, maxint).
mplus(_, minint, minint).
mplus(_, maxint, maxint).
mplus(A, B, C) :-
        A \== minint,
        A \== maxint,
        B \== minint,
        B \== maxint,
        C \== minint,
        C \== maxint,
        plus(A, B, C).

goal_in_range(V, A, B, G) :-
        goal_leq(A, B, GCheck),
        (GCheck ->
            goal_leq(A, V, G1),
            goal_leq(V, B, G2),
            goal_conj(G1, G2, G)
        ;
        G = fail).

condition_test(indirect(_), _) :- !.
condition_test(Cond, V) :-
        condition_range(Cond, A:B),
        goal_in_range(V, A, B, G),
        G.

goal_nonemptycondition(Cond, G) :-
        condition_range(Cond, A:B),
        goal_leq(A, B, G).

goal_subcondition(C1, C2, G) :-
        condition_range(C1, A1:B1),
        condition_range(C2, A2:B2),
        goal_leq(A2, A1, G1),
        goal_leq(B1, B2, G2),
        goal_conj(G1, G2, G).

condition_type(Cond, singleton(A)) :-
        condition_range(Cond, A:B),
        goal_leq(B, A, G), G.
condition_type(Cond, char) :-
        goal_subcondition(Cond, char, G), G.
condition_type(Cond, code_t) :-
        goal_subcondition(Cond, byte, G), G.
condition_type(indirect(T), T).
condition_type(_, word_t).


% instruction helpers
unary_insn(Name, Name) :- unary_insn(Name).
binary_insn(Name, Name) :- binary_insn(Name).

overflow_code(Name, Args, Ovf, [flag(set)]) :-
        overflow_flag(Name),
        !,
        Op =.. [macro_args | Args],
        Ovf = [setflag=ovf_check(Name, Op)].
overflow_code(_, _, [], []).

build_simple_insn(Name, COp, Code, Args, Opts) :-
        Code = [out(0) = Op | OvfCode],
        Op =.. [COp | Args],
        overflow_code(Name, Args, OvfCode, Opts).

insn(Name, [], Code, [stack(1->1)|Opts]) :-
        unary_insn(Name, COp),
        atom(COp),
        build_simple_insn(Name, COp, Code, [in(0)], Opts).

insn(Name, [], Code, [stack(2->1)|Opts]) :-
        binary_insn(Name, COp),
        atom(COp),
        build_simple_insn(Name, COp, Code, [in(1), in(0)], Opts).

%insn(Name, [], Code, [stack(1->N)]) :-
%        unary_insn(Name, COp),
%        is_list(COp),
%        length(COp, N),
%        build_insn(COp, [in(0)], Code).
%
%insn(Name, [], Code, [stack(2->N)]) :-
%        binary_insn(Name, COp),
%        is_list(COp),
%        length(COp, N),
%        build_insn(COp, [in(1), in(0)], Code).
%
%build_insn([COp1|Tail], CArgs, [out(TN) = Op | CodeTail]) :-
%        Op =.. [COp1 | CArgs],
%        length(Tail, TN),
%        build_insn(Tail, CArgs, CodeTail).
%build_insn([], _, []).


% combined instructions
mode_pair(Modes, StdMode) :-
        mode_combine(MList),
        %append(MList1, _, MList),
        %Modes = [_|_],
        append(Modes, [StdMode], MList).


% insn_mode([insn(conditions...), insn(conditions...), ...])

% register all standard modes for a single instruction
insn_single_mode(Insn, StdMode, InputStack) :-
        insn(Insn, Args, _, Options),
        \+ memberchk(suffixonly, Options),
        % the first arg of standard_mode/4 is a singleton var that must
        % unify to the same atom for all the arguments.  In other words
        % we are only interested in condlists containing all small or all
        % large conditions.
        maplist(standard_mode(_, InputStack), Args, CondList),
        StdMode =.. [Insn | CondList].

insn_mode([StdMode]) :-
        initial_stack(Stack),
        insn_single_mode(_, StdMode, Stack).

% register combined modes
insn_mode(MList) :-
        mode_pair(Modes, StdMode),
        append(Modes, [StdMode], MList).

standard_mode(small, _,  i, char).
standard_mode(large, _,  i, int).
standard_mode(_,     _,  l, indirect(word_t)).
standard_mode(_,     _,  b, indirect(code_t)).
standard_mode(Sz, Stack, s, Cond) :-
        standard_mode_stack(Stack, Sz, 0, Cond).

standard_mode_stack(push(_, _), _, N, N).
standard_mode_stack(push(_, Queue), Sz, N, Cond) :-
        N1 is N+1,
        standard_mode_stack(Queue, Sz, N1, Cond).
standard_mode_stack(slice(_), small, N, N:255).
standard_mode_stack(slice(_), large, N, N:maxint).

% convert between mode and opcode number
:- det(mode_opcode/2).
mode_opcode(Mode, Opcode) :-
        enumerate(insn_mode(M), Opcode, 1),
        (M = Mode ; M = [Mode]),
        !.

% context stack manipulation
%initial_stack(slice(0)).
initial_stack(push(accum, slice(0))).
%initial_stack(push(accum, push(accum2, slice(0)))).

initial_stack_depth(N) :-
        initial_stack(S0), stack_depth(S0, N).

cell_length(push(_, Tail), Ns) :-
        cell_length(Tail, N),
        succ(N, Ns).
cell_length(slice(_), 0).

stack_depth(push(_, Tail), Ns) :-
        stack_depth(Tail, N),
        succ(N, Ns).
stack_depth(slice(ExtraPops), N) :-
        plus(ExtraPops, N, 0).

% stack_top(+-Item, +-Tail, -+Stack)  <=>  Stack = push(Item, Tail)
stack_top(Item, Tail, push(Item, Tail)) :- !.
stack_top(Item, slice(Ns), slice(N)) :-
        succ(N, Ns),
        stack_nth(slice(N), 0, Item).

% stack_nth(+Stack, +N, -Item)
stack_nth(push(Item, _), 0, Item).
stack_nth(push(_, Tail), Ns, Item) :-
        succnat(N, Ns),
        stack_nth(Tail, N, Item).
stack_nth(slice(ExtraPops), N, stack_nth(P)) :-
        plus(N, ExtraPops, P).

% stack_shift(+stack_nth(N), +Shift, -stack_nth(N+Shift))
stack_shift(stack_nth(N), Shift, stack_nth(M)) :-
        plus(N, Shift, M),
        !.
stack_shift(Item, _, Item).


% instruction stack operations
:- det(insn_stack/4).
insn_stack(none, Stack, Stack, _).

insn_stack(push, OldStack, NewStack, X) :-
        insn_stack(0->1, OldStack, NewStack, X).
insn_stack(pop, OldStack, NewStack, X) :-
        insn_stack(1->0, OldStack, NewStack, X).
insn_stack(pop(0), OldStack, NewStack, X) :-
        insn_stack(1->0, OldStack, NewStack, X).
insn_stack(pop(Ns), OldStack, NewStack, X) :-
        succnat(N, Ns),
        stack_top(Top, S1, OldStack),
        insn_stack(pop(N), S1, S2, X),
        stack_top(Top, S2, NewStack).

%insn_stack(swap, OldStack, NewStack) :-
%        stack_top(X1, S1, OldStack),
%        stack_top(X2, S2, S1),
%        stack_top(X1, S2, S3),
%        stack_top(X2, S3, NewStack).

insn_stack(unary, OldStack, NewStack, X) :-
        insn_stack(1->1, OldStack, NewStack, X).
insn_stack(binary, OldStack, NewStack, X) :-
        insn_stack(2->1, OldStack, NewStack, X).

insn_stack(0->0, Stack, Stack, _).
insn_stack(0->Ns, OldStack, NewStack, X) :-
        succnat(N, Ns),
        stack_top(_, OldStack, S1),  % push a new unnamed variable
        insn_stack(0->N, S1, NewStack, X).
insn_stack(Ms->N, OldStack, NewStack, X) :-
        succnat(M, Ms),
        stack_top(_, S1, OldStack),  % pop away the first element
        insn_stack(M->N, S1, NewStack, X).

insn_stack(settos, _, NewStack, extra([_:_|_],[stack_nth(N)])) :-
        NewStack = trashed(N).   % optimization for the next line
        %NewStack = specialop(stack_shift(N), OldStack).
insn_stack(settos, OldStack, NewStack, extra([N|_], _)) :-
        integer(N),
        insn_stack(N->0, OldStack, NewStack, _).
insn_stack(pushn, OldStack, NewStack, extra(_, [N])) :-
        NewStack = specialop(stack_shift(-N), OldStack).

:- det(insn_operate_stack/4).
insn_operate_stack(Insn, OldStack, NewStack, Extra) :-
        insn(Insn, _, _, Options),
        (memberchk(stack(StackOp), Options), !; StackOp = none),
        insn_stack(StackOp, OldStack, NewStack, Extra).
insn_operate_stack(Insn, OldStack, NewStack) :-
        insn_operate_stack(Insn, OldStack, NewStack, dummy).

:- det(insn_operate_flag/3).
insn_operate_flag(Insn, OldFlag, NewFlag, PreCode, PostCode) :-
        insn(Insn, _, _, Options),
        (memberchk(flag(get), Options) ->
            PreCode = [impl_debug_check_flag(OldFlag)],
            PostCode = [impl_debug_forget_flag(OldFlag)],
            NewFlag = consumed
        ;
        PreCode = [],
        PostCode = [],
        (memberchk(flag(set), Options) ->
            true   % NewFlag stays a variable
        ;
        NewFlag = OldFlag)).

map_operate((OldStack,_), _, _, in(N),  Item) :- !, stack_nth(OldStack, N, Item).
map_operate(_, (NewStack,_), _, out(N), Item) :- !, stack_nth(NewStack, N, Item).
map_operate(_, _,    InputArgs, arg(N), Item) :- !, nth0(N, InputArgs, Item).
map_operate((OldStack,_), _, _, stkshft, N) :- !, stack_depth(OldStack, N).
map_operate((_,OldFlag),  _, _, flag,    OldFlag) :- !.
map_operate(_, (_,NewFlag),  _, setflag, NewFlag) :- !.
map_operate(P1, P2, P3, Compound, Item) :-
        Compound =.. [Functor|Args],
        !,
        maplist(map_operate(P1, P2, P3), Args, MappedArgs),
        Item =.. [Functor|MappedArgs].
map_operate(_, _, _, Item, Item).

map_operate_top(P1, P2, P3, X=Y, []) :-
        map_operate(P1, P2, P3, X, Item1), var(Item1),
        map_operate(P1, P2, P3, Y, Item2), var(Item2),
        Item1 = Item2,
        !.
map_operate_top(P1, P2, P3, Input, Item) :-
        map_operate(P1, P2, P3, Input, Item).

:- det(insn_operate_code/5).
insn_operate_code(Insn, OldState, NewState, InputArgs, Code) :-
        insn(Insn, _, CodeTemplate, _),
        maplist(map_operate_top(OldState, NewState, InputArgs),
                CodeTemplate, Code).

:- det(load_initexpr/5).
load_initexpr(CurrentStack, s, Cond, _, A2) :-
        condition_range(Cond, N:N),
        stack_nth(CurrentStack, N, A2),
        !.
load_initexpr(slice(0), s, Cond, A1, stack_nth(A1)) :-
        condition_range(Cond, A:_),
        goal_leq(0, A, G), G,
        !.
load_initexpr(slice(ExtraPops), s, Cond, A1, stack_nth(A1+ExtraPops)) :-
        condition_range(Cond, A:_),
        goal_leq(0, A, G), G,
        !.
load_initexpr(slice(_), s, Cond, _, _) :-
        user_error('*** Reading too deep from the stack', Cond).
load_initexpr(push(_, TailStack), s, Cond, A1, stack_nth(A2-1)) :-
        load_initexpr(TailStack,  s, Cond-1, A1, stack_nth(A2)),
        !.
load_initexpr(_, _, _, V, V).

:- det(init_arg/3).
init_arg(Cond, [], A) :-
        condition_type(Cond, singleton(A)),
        !.
init_arg(Cond, V=bytecode_next(T), V) :-
        condition_type(Cond, T),
        !.

:- det(size_arg/2).
size_arg(Cond, 0) :-
        condition_type(Cond, singleton(_)),
        !.
size_arg(Cond, bytecode_size(T)) :-
        condition_type(Cond, T),
        !.

:- det(mode_operate1/3).
mode_operate1(Mode, (Stack1, Flag1, InitU1, CodeL1),
                    (Stack2, Flag2, InitU2, CodeL2)) :-
        Mode =.. [Insn|CondList],
        insn(Insn, Args, _, _),
        maplist(init_arg, CondList, InitUnif, InitArgs),
        maplist(load_initexpr(Stack1), Args, CondList, InitArgs, UseArgs),
        insn_operate_stack(Insn, Stack1, Stack2, extra(CondList, UseArgs)),
        insn_operate_flag(Insn, Flag1, Flag2, FlagPreCode, FlagPostCode),
        insn_operate_code(Insn, (Stack1, Flag1), (Stack2, Flag2), UseArgs, Code),
        append(InitU1, InitUnif, InitU2),
        append(CodeL1, FlagPreCode, Code, FlagPostCode, CodeL2).

:- det(mode_operate/2).
mode_operate(Mode, block_locals(word_t, CodeBlock)) :-
        initial_stack(OldStack),
        chainlist(mode_operate1, Mode,
                  (OldStack, flag, [], []), (NewStack, NewFlag, U1, C3)),
        mode_unify((NewStack, NewFlag), (OldStack, flag), C4),
        append(U1, C3, C4, CodeBlock1),
        code_simplify(CodeBlock1, CodeBlock).

mode_nonclobber_flag(Mode) :-
        initial_stack(OldStack),
        chainlist(mode_operate1, Mode,
                  (OldStack, _, [], []), (_, NewFlag, _, _)),
        var(NewFlag).

% stack_unify(+CurrentStack, +TargetStack, -UnificationsList1, -2, -StackShift)
stack_unify(slice(E1), slice(E2), [], [], StackShift) :-
        !,
        plus(E2, StackShift, E1).
stack_unify(trashed(N), TargetStack, UnifList1, UnifList2, StackShift) :-
        !,
        stack_unify(slice(0), TargetStack, UnifL1, UnifList2, StackShift),
        UnifList1 = [stack_shift(N) | UnifL1].
stack_unify(specialop(Op, Cur), TargetStack, UnifList1, UnifList2, StackShift) :-
        !,
        stack_unify(Cur, slice(0), UnifL1, UnifL2, StackShift1),
        UnifExtra = [stack_shift(StackShift1), Op],
        stack_unify(slice(0), TargetStack, UnifL1bis, UnifList2, StackShift),
        reverse(UnifL2, UnifL2r),
        append(UnifL1, UnifL2r, UnifExtra, UnifL1bis, UnifList1).
stack_unify(CurrentStack, TargetStack, UnifList1, UnifList2, StackShift) :-
        stack_top(Src,     S1, CurrentStack),
        stack_top(PreDest, S2, TargetStack),
        stack_unify(S1, S2, UnifL1, UnifL2, StackShift),
        stack_shift(PreDest, StackShift, Dest),
        (Src == Dest ->
            UnifList1 = UnifL1,
            UnifList2 = UnifL2
        ;
        UnifList1 = [Temp=Src | UnifL1],
        UnifList2 = [Dest=Temp | UnifL2]).

:- det(mode_unify/3).
mode_unify((S1,F1), (S2,F2), Code) :-
        stack_unify(S1, S2, UnifList1, UnifList2, StackShift),
        reverse(UnifList2, UnifList2r),
        (StackShift > 0 ->
            CodeL4 = [stack_shift_pos(StackShift)|CodeTail]
        ;
        (StackShift < 0 ->
            CodeL4 = [stack_shift(StackShift)|CodeTail]
        ;
        CodeL4 = CodeTail)),
        (var(F1) ->
            CodeTail = [F2=F1]
        ;
        CodeTail = []),
        append(UnifList1, UnifList2r, CodeL4, Code).

% instruction emitters
insn_inputargname((_, Index), Name) :-
        int_to_atom(Index, Suffix),
        atom_concat(arg, Suffix, Name).

insn_inputargtype(s, 'int') :- !.
insn_inputargtype(l, 'word_t**') :- !.
insn_inputargtype(b, 'code_t**') :- !.
insn_inputargtype(_, 'word_t').

insn_declarearg(Name, Type, var(Type, Name)).

insn_defarglist(Insn, ArgList) :-
        insn(Insn, Args, _, _),
        enumerate_list(Args, NumberedArgs, 1, _),
        maplist(insn_inputargname, NumberedArgs, ArgNames),
        maplist(insn_inputargtype,         Args, ArgTypes),
        maplist(insn_declarearg, ArgNames, ArgTypes, ArgList).

%insn_preparearg(s, Name, ModifiedName, [var(int, ModifiedName, Init)]) :-
%        !,
%        atom_concat(Name, s, ModifiedName),
%        Init = 'CURRENT_STACK_POSITION'(Name).
insn_preparearg(_, Name, Name, []).

mode_outputargtype(_, l, 'placeholder_long').
mode_outputargtype(_, b, 'placeholder_byte').
mode_outputargtype(Cond, _, void) :-
        condition_range(Cond, A:A).
mode_outputargtype(Cond, _, char) :-
        goal_subcondition(Cond, char, G), G.
mode_outputargtype(Cond, _, byte) :-
        goal_subcondition(Cond, byte, G), G.
mode_outputargtype(_, s, 'int').
mode_outputargtype(_, _, 'word_t').

mode_conditions(Mode, Conditions) :-
        Mode =.. [_ | Conditions].

mode_emitarg(Cond, Arg, V, emit(Type, V)) :-
        mode_outputargtype(Cond, Arg, Type),
        !.

:- det(mode_emit/4).
mode_emit(PrevMode, Mode, InputArgs, Code) :-
        Mode =.. [Insn | Conditions],
        insn(Insn, Args, _, _),
        append(PrevMode, [Mode], FullMode),
        mode_opcode(FullMode, Opcode),
        (PrevMode = [] ->
            Emitter = emit(opcode, Opcode)
        ;
            joinlist(mode_conditions, PrevMode, PrevConditions),
            maplist(size_arg, PrevConditions, Sizes),
            chainlist(goal_add, Sizes, 0, TotalSize),
            Emitter = emit(modified_opcode, Opcode, TotalSize)
        ),
        maplist(mode_emitarg, Conditions, Args, InputArgs, CodeL2),
        append([Emitter], CodeL2, [setlatestopcode(Opcode), return(code)], Code).

:- det(insn_definemode/5).
insn_definemode(InputArgs, PrevMode, Mode, Code, ElseCode) :-
        Mode =.. [_ | Conditions],
        maplist(goal_condition, Conditions, InputArgs, Goals),
        chainlist(goal_conj, Goals, true, FinalGoal),
        Code = ifte(FinalGoal, CodeL1, ElseCode),
        mode_emit(PrevMode, Mode, InputArgs, CodeL1).

insn_combination(InputArgs, Insn, Case) :-
        % setof backtracks over each value of PrevMode,
        % giving for each a list of possible Modes.
        setof(Mode, Cond^(mode_pair(PrevMode, Mode), Mode=..[Insn|Cond]),
              Modes),
        mode_opcode(PrevMode, Opcode),
        Case = case(Opcode, [comment(PrevMode), Body1]),
        chainlist(insn_definemode(InputArgs, PrevMode), Modes,
                  Body1, FinalCase),
        FinalCase = break.

:- det(insn_defbody/2).
insn_defbody(Insn, block(DeclCode, BodyCode)) :-
        insn(Insn, Args, _, Options),
        %(memberchk(flag(get), Options) ->
        %    BodyCode = [extra_assert('FLAG_NONCLOBBERING'('LATEST_OPCODE')) |
        %                MainBodyCode]
        %;
        MainBodyCode = BodyCode,
        enumerate_list(Args, NumberedArgs, 1, _),
        maplist(insn_inputargname, NumberedArgs, ArgNames),
        joinlist(insn_preparearg, Args, ArgNames, InputArgs, DeclCode),
        MainBodyCode = [switch('LATEST_OPCODE', Cases) | RegularBodyCode],
        findall(Code, insn_combination(InputArgs, Insn, Code), Cases),
        initial_stack(InitialStack),
        findall(StdMode, insn_single_mode(Insn,StdMode,InitialStack), StdModes),
        chainlist(insn_definemode(InputArgs, []), StdModes,
                  RegularBodyCode, FinalCase),
        (memberchk(suffixonly, Options) ->
            FinalCase = [comment('suffix only'), return(code)]
        ;
            FinalCase = error(invalid_mode(Insn))
        ).

:- det(insn_define/4).
insn_define(Insn, Insn, ArgList, Body) :-
        insn_defarglist(Insn, ArgList),
        insn_defbody(Insn, Body1),
        code_simplify(Body1, Body).
