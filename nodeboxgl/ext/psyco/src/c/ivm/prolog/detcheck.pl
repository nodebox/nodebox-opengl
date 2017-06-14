:- dynamic detchecked/1, detdebug/0.

det(Functor/Arity) :-
        ignore(retract(detchecked(Functor/Arity))),
        assert(detchecked(Functor/Arity)),
        length(Args, Arity),
        Head =.. [Functor | Args],
        atom_concat('__detcheck$', Functor, MangledFunctor),
        MangledHead =.. [MangledFunctor | Args],
        ignore(retract(Head :- _)),
        assert(Head :- ((detdebug -> writeq(Head), nl ; true), MangledHead, ! ;
                        deterror(Head))).

deterror(Head) :-
        user_error('*** Predicate call should not have failed:', Head).

user_error(Msg, Object) :-
        tell(user_error),
        nl,
        write(Msg),
        nl,
        write_term(Object, [quoted(true), max_depth(8)]),
        nl,
        throw(user_error).


term_expansion(Head :- Body, MangledHead :- Body) :-
        !,
        term_expansion(Head, MangledHead).

term_expansion(Head, MangledHead) :-
        Head =.. [Functor | Args],
        length(Args, Arity),
        detchecked(Functor/Arity),
        !,
        atom_concat('__detcheck$', Functor, MangledFunctor),
        MangledHead =.. [MangledFunctor | Args].
