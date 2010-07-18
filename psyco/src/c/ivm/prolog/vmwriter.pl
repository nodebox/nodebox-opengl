:- consult(vm).
:- discontiguous main_emit/2.


% large-scale code emission: the virtual machine interpreter
main_emit(modes, switch) :-
        (
            enumerate(insn_mode(M), Opcode, 1),
            mode_operate(M, Code),
            format('case ~d:  /* ~w */\n', [Opcode, M]),
            write_codestmt(Code),
            write('continue;\n\n'),
            fail
        ;
        true).


threaded_table(absolute, 'void*',
        '  &&lblopcode~d,  /* ~w */\n',
        '  &&lblorigin,    /* ~d */\n').
threaded_table(relative, 'int',
        '  &&lblopcode~d - &&lblorigin,  /* ~w */\n',
        '  0,  /* ~d */\n').

threaded_initial(_) :-
        write('lblorigin:\npsyco_fatal_msg("invalid vm opcode");\n\n').

threaded_jump(absolute) :-
        write('goto *opcodetable[bytecode_nextopcode()];\n\n').
threaded_jump(relative) :-
        write('goto *(&&lblorigin + opcodetable[bytecode_nextopcode()]);\n\n').

main_emit(modes, threaded(Origin)) :-
        threaded_table(Origin, CType, LineFormatStr, MissingFormatStr),
        format('static const ~w opcodetable[] = {\n', [CType]),
        format(MissingFormatStr, [0]),
        (
            enumerate(insn_mode(M), Opcode, 1),
            format(LineFormatStr, [Opcode, M]),
            fail
        ;
        countsuccesses(insn_mode(_), NbOpcodes),
        FirstMissing is NbOpcodes+1,
        write('#if PSYCO_DEBUG\n'),
        (
            between(FirstMissing, 255, Opcode),
            format(MissingFormatStr, [Opcode]),
            fail
        ;
        write('#endif\n'),
        write('};\n'),
        threaded_jump(Origin),
        threaded_initial(Origin),
        (
            enumerate(insn_mode(M), Opcode, 1),
            mode_operate(M, Code),
            format('lblopcode~d:  /* ~w */\n', [Opcode, M]),
            write_codestmt(Code),
            threaded_jump(Origin),
            fail
        ;
        true))).

% emits only the definition of a single instruction
main_emit(modes, single(Mode)) :-
        mode_operate(Mode, Code),
        write_codestmt(Code).


% large-scale code emission: the instruction writer helpers
insn_definition(MacroName, MacroArgList, FunctionName, FunctionArgList, Body,
                SingleInstr) :-
        insn(Insn, _, _, _),
        insn_define(Insn, Name, MacroArgList, Body),
        atom_concat('INSN_', Name, MacroName),
        (Body=block([],[emit(opcode,Op),setlatestopcode(Op)|return(_)]) ->
            % macro only
            SingleInstr = emit(macro_opcode, Op),
            FunctionName = ''
        ;
        atom_concat('psyco_insn_', Name, FunctionName),
        FunctionArgList = [var('code_t*', code) | MacroArgList]).

main_emit(insns, headers(Prefix)) :-
        countsuccesses(insn_mode(_), NbOpcodes),
        (NbOpcodes > 255 -> user_error('too many opcodes', NbOpcodes) ; true),
        write('#define LAST_DEFINED_OPCODE '),
        write(NbOpcodes),
        nl,
        nl,
        (
            insn_definition(MacroName, MacroArgList,
                            FunctionName, FunctionArgList, _, SingleInstr),
            write('#define '),
            write_code(macro_call(MacroName, MacroArgList)),
            write(' '),
            (FunctionName = '' ->
                % write as a macro
                write_code(SingleInstr),
                nl
            ;
                % write as a call to an EXTERN function
                write('(code = '),
                write_code(macro_call(FunctionName, FunctionArgList)),
                write(')'),
                nl,
                write(Prefix),
                write_code(function_header(FunctionName, 'code_t*',
                                           FunctionArgList)),
                write(';'),
                nl),
            fail
        ;
        true).

main_emit(insns, functions(Prefix)) :-
        %write('#define FLAG_NONCLOBBERING(op) ( \\'), nl,
        %(
        %    enumerate(insn_mode(M), Opcode, 1),
        %    mode_nonclobber_flag(M),
        %    write('\t(op)=='), write(Opcode), write(' || \\\n'),
        %    fail
        %;
        %write('\t0)\n'),
        (
            insn_definition(_, _, FunctionName, FunctionArgList, Body, _),
            (FunctionName = '' ->
                % only exists as a macro
                true
                ;
                % write the function definition
                nl,
                write(Prefix),
                write_code(function_def(FunctionName, 'code_t*',
                                        FunctionArgList, Body))),
            fail
        ;
        true).

% write the instruction table in Python
:- det(objdump_mode/2).
:- det(objdump_insn/1).

objdump_mode(Opcode, M) :-
        format('  ~d: [', [Opcode]),
        maplist(objdump_insn, M),
        write('],'),
        nl.

objdump_insn(M) :-
        M =.. [Insn | Args],
        insn(Insn, ArgLetters, _, _),
        format('("~w",', [Insn]),
        maplist(objdump_arg, Args, ArgLetters),
        write('), ').

objdump_arg(_:255, s) :- !,
        write(stack(byte)),
        write(',').
objdump_arg(_:maxint, s) :- !,
        write(stack(long)),
        write(',').
objdump_arg(A, s) :- !,
        write(stack(A)),
        write(',').
objdump_arg(A, _) :-
        write(A),
        write(',').

objdump_stackpushes(M, P) :-
        chainlist(objdump_stackpush, M, 0, P).

objdump_stackpush(M, P1, P2) :-
        M =.. [Insn | _],
        count_stackpush(Insn, P),
        P2 is P1+P.

count_stackpush(Insn, P) :-
        insn(Insn, _, _, Options),
        \+ memberchk(nostackanalysis, Options),
        (memberchk(stack(StackOp), Options) -> true ; StackOp = none),
        objdump_stackop(StackOp, P).

objdump_chainables(M) :-
        maplist(objdump_chainable, M).

objdump_chainable(M) :-
        M =.. [Insn | _],
        chainable(Insn).

chainable(Insn) :-
        insn(Insn, _, _, Options),
        \+ memberchk(nonchainable, Options).

objdump_stackop(none,   0).
objdump_stackop(push,   1).
objdump_stackop(pop,    -1).
objdump_stackop(pop(_), -1).
objdump_stackop(N->M,   P) :- P is M-N.
objdump_stackop(unary,  0).
objdump_stackop(binary, -1).

main_emit(pytable) :-
        write('insntable = {'),
        nl,
        (
            enumerate(insn_mode(M), Opcode, 1),
            objdump_mode(Opcode, M),
            fail
        ;
        write('}'),
        nl,
        write('stackpushes = {'),
        nl,
        (
            enumerate(insn_mode(M), Opcode, 1),
            objdump_stackpushes(M, P),
            format('  ~d: ~d,\n', [Opcode, P]),
            fail
        ;
        write('}'),
        nl,
        write('chainable = {'),
        nl,
        (
            enumerate(insn_mode(M), Opcode, 1),
            objdump_chainables(M),
            format('  ~d: 1,\n', [Opcode]),
            fail
        ;
        write('}'),
        nl))).


% generate all files
main_emit :-
        tell('insns-igen-h.i'), main_emit(insns, headers('EXTERNFN ')), told,
        tell('insns-igen.i'), main_emit(insns, functions('DEFINEFN ')), told,
        tell('insns-threaded.i'), main_emit(modes, threaded(absolute)), told,
        tell('insns-switch.i'), main_emit(modes, switch), told,
        tell('insns-table.py'), main_emit(pytable), told.
