:- consult(utils).
:- multifile goal_to_C/2, unary_prolog_to_C/2, binary_prolog_to_C/2.


unary_prolog_to_C(not,    '!').
unary_prolog_to_C(inv,    '~').
unary_prolog_to_C('-',    '-').
unary_prolog_to_C(addr,   '(word_t) &').
unary_prolog_to_C(unsigned, '(unsigned)').
unary_prolog_to_C(mem1,  '*(char*)').
unary_prolog_to_C(mem1u, '*(unsigned char*)').
unary_prolog_to_C(mem2,  '*(short*)').
unary_prolog_to_C(mem2u, '*(unsigned short*)').
unary_prolog_to_C(mem4,  '*(long*)').
unary_prolog_to_C(cast1, '(char)').
unary_prolog_to_C(cast2, '(short)').

binary_prolog_to_C('=',   '=').
binary_prolog_to_C('=<',  '<=').
binary_prolog_to_C('<',   '<').
binary_prolog_to_C('>=',  '>=').
binary_prolog_to_C('>',   '>').
binary_prolog_to_C('=:=', '==').
binary_prolog_to_C('=/=', '!=').
binary_prolog_to_C('>>',  '>>').
binary_prolog_to_C('<<',  '<<').
binary_prolog_to_C(or,    '|').
binary_prolog_to_C(and,   '&').
binary_prolog_to_C(xor,   '^').
binary_prolog_to_C(',',   '&&').

goal_to_C(fail, '0').
goal_to_C(true, '1').
goal_to_C(c_unary(COp, X), Code) :-
        goal_to_C(X, XCode),
        concat_atom(['(', COp, XCode, ')'], Code).
goal_to_C(c_binary(COp, X, Y), Code) :-
        goal_to_C(X, XCode1),
        goal_to_C(Y, YCode1),
        (COp = '=' ->
            remove_paren(XCode1, XCode),
            remove_paren(YCode1, YCode)
        ;
            XCode1 = XCode,
            YCode1 = YCode
        ),
        concat_atom(['(', XCode, ' ', COp, ' ', YCode, ')'], Code).

goal_to_C(Term, Code) :-
        Term =.. [PrologOp, Arg1, Arg2],
        binary_prolog_to_C(PrologOp, COp),
        goal_to_C(c_binary(COp, Arg1, Arg2), Code).
goal_to_C(Term, Code) :-
        Term =.. [PrologOp, Arg1],
        unary_prolog_to_C(PrologOp, COp),
        goal_to_C(c_unary(COp, Arg1), Code).
goal_to_C(Term, Code) :-
        Term =.. [Code].
goal_to_C(Term, Code) :-
        Term =.. [Functor | Args],
        maplist(goal_to_C, Args, ArgsCode),
        NewTerm =.. [Functor | ArgsCode],
        sformat(SCode, '~w', [NewTerm]),
        string_to_atom(SCode, Code).

%goal_to_C([], '').
%goal_to_C([H|T], Code) :-
%        goal_to_C(H, Code1),
%        goal_to_C(T, Code2),
%        concat_atom([Code1, ';\n', Code2], Code).

remove_paren(Inp, Outp) :-
        sub_atom(Inp, 0, _, _, '('),
        sub_atom(Inp, _, _, 0, ')'),
        sub_atom(Inp, 1, _, 1, Outp),
        !.
remove_paren(C, C).

% C structures
declare_local(Type, (V, Index), var(Type, V)) :-
        int_to_atom(Index, Suffix),
        atom_concat(local, Suffix, V).

block_locals(CodeL1, Type, block(DeclList, CodeL1)) :-
        free_variables(CodeL1, FreeVars),
        enumerate_list(FreeVars, NumberedFreeVars, 1, _),
        maplist(declare_local(Type), NumberedFreeVars, DeclList).

% C code emission
write_codelist([], _, _).
write_codelist([C1], _, EndSep) :-
        write_code(C1),
        write(EndSep).
write_codelist([C1, C2 | Tail], MiddleSep, EndSep) :-
        write_code(C1),
        write(MiddleSep),
        write_codelist([C2 | Tail], MiddleSep, EndSep).

arg_name_only(var(_, V), var(V)).

write_code1(var(V)) :-
        write(V).

write_code1(var(Type, V)) :-
        write(Type), write(' '), write(V).

write_code1(var(Type, V, Init)) :-
        write(Type), write(' '), write(V), write(' = '),
        write_code(Init).

write_code1(function_header(Name, RetType, ArgList)) :-
        write(RetType), write(' '),
        write(Name), write('('),
        (ArgList = [] ->
            write(void)
        ;
            write_codelist(ArgList, ', ', '')
        ),
        write(')').

write_code1(macro_call(Name, ArgList)) :-
        write(Name), write('('),
        maplist(arg_name_only, ArgList, ArgList1),
        write_codelist(ArgList1, ', ', ''),
        write(')').

write_code1(function_def(Name, RetType, ArgList, Body)) :-
        write_code(function_header(Name, RetType, ArgList)),
        nl,
        write_codestmt(Body).

write_code1(error(Descr)) :-
        write('psyco_fatal_msg("'),
        write(Descr),
        write('");\nreturn NULL').

write_code1(comment(Descr)) :-
        write('/* '),
        write(Descr),
        write(' */').

write_code1(emit(Type, Value)) :-
        write('INSN_EMIT_'),
        write(Type),
        write('('),
        write(Value),
        write(')').

write_code1(emit(Type, Value, Extra)) :-
        write('INSN_EMIT_'),
        write(Type),
        write('('),
        write(Value),
        write(', '),
        write(Extra),
        write(')').

write_code1(Expr) :-
        goal_to_C(Expr, Code),
        remove_paren(Code, Code1),
        write(Code1).

:- det(write_code/1).
write_code(Code) :-
        write_code1(Code),
        !.

write_codestmt1([]).
write_codestmt1([H|T]) :-
        write_codestmt(H),
        write_codestmt(T).

write_codestmt1(block(DeclList, CodeList)) :-
        write('{\n'),
        write_codelist(DeclList, ';\n', ';\n'),
        write_codestmt(CodeList),
        write('}\n').

write_codestmt1(block_locals(Type, CodeList)) :-
        block_locals(CodeList, Type, Outp),
        write_codestmt(Outp).

write_codestmt1(ift(Cond, Then)) :-
        write('if ('),
        write_code(Cond),
        write(') '),
        write_codeblock(Then).

write_codestmt1(ifte(Cond, Then, Else)) :-
        write('if ('),
        write_code(Cond),
        write(') '),
        write_codeblock(Then),
        write('else '),
        write_codeblock(Else).

write_codestmt1(switch(Expr, Body)) :-
        write('switch ('),
        write_code(Expr),
        write(') {\n'),
        write_codestmt(Body),
        write('} /* switch */\n').

write_codestmt1(case(Expr, Body)) :-
        write('case '),
        write_code(Expr),
        write(':\n'),
        write_codeblock(Body).

write_codestmt1(comment(Descr)) :-
        write('/* '),
        write(Descr),
        write(' */\n').

write_codestmt1(Expr) :-
        write_code(Expr),
        write(';\n').

:- det(write_codestmt/1).
write_codestmt(Code) :-
        write_codestmt1(Code),
        !.

write_codeblock(Block) :-
        write_codestmt(block([], Block)).

code_simplify1([], []).
code_simplify1([Code1], Code2) :-
        code_simplify1(Code1, Code2).
code_simplify1([H1|T1], Code2) :-
        code_simplify1(H1, H2),
        code_simplify1(T1, T2),
        (H2 = [] -> Code2 = T2 ;
            (T2 = [] -> Code2 = H2 ;
                Code2 = [H2|T2])).

code_simplify1(block([], block(Decl1, Body1)), Code2) :-
        code_simplify1(block(Decl1, Body1), Code2).
code_simplify1(block(Decl, Stmt1), block(Decl, Stmt2)) :-
        code_simplify1(Stmt1, Stmt2).

code_simplify1(ift(true, Then), Code2) :-
        code_simplify1(Then, Code2).
code_simplify1(ift(fail, _), []).

code_simplify1(ifte(true, Then, _), Code2) :-
        code_simplify1(Then, Code2).
code_simplify1(ifte(fail, _, Else), Code2) :-
        code_simplify1(Else, Code2).

code_simplify1(switch(_, []), []).
code_simplify1(switch(Expr, Body1), switch(Expr, Body2)) :-
        code_simplify1(Body1, Body2).

code_simplify1(case(Expr, Body1), case(Expr, Body2)) :-
        code_simplify1(Body1, Body2).

code_simplify1(Code, Code).

:- det(code_simplify/1).
code_simplify(Code1, Code2) :-
        code_simplify1(Code1, Code2),
        !.


trivial_c_arg(Term) :- var(Term).
trivial_c_arg(Term) :- Term =.. [_].

trivial_c_op(X=Y) :- trivial_c_arg(X), trivial_c_arg(Y).
trivial_c_op(extra_assert(_)).

codecost(block_locals(_, L), Cost) :-
        closelist(L, FlatL),
        countsuccesses((member(X, FlatL), \+trivial_c_op(X)), Cost).
