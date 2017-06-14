:- consult(detcheck).

% succnat(N, N+1) only with N>=0
succnat(N, Ns) :- succ(N, Ns), N>=0.

% same as reverse/2, but accepts any instantiation pattern.
reverse1([], []).
reverse1([H1|T1], [H2|T2]) :-
        same_length(T1, T2, T2r),
        append(T2r, [H2], [H1|T1]),
        reverse1(T2, T2r).

same_length([], []).
same_length([_|T1], [_|T2]) :-
        same_length(T1, T2).

same_length([], [], []).
same_length([_|T1], [_|T2], [_|T3]) :-
        same_length(T1, T2, T3).

% longer versions of append.
% Deterministic if all arguments but the last one are bound.
% Finitely backtracking if the last argument is bound.
append(L1, L2, L3, L123) :-
        append(L1, L23, L123),
        append(L2, L3, L23).
append(L1, L2, L3, L4, L1234) :-
        append(L1, L234, L1234),
        append(L2, L34, L234),
        append(L3, L4, L34).

% a shorter and some longer versions of maplist.
maplist(_Pred, []).
maplist(Pred, [H1|T1]) :-
        call(Pred, H1),
        maplist(Pred, T1).
maplist(_Pred, [], [], []).
maplist(Pred, [H1|T1], [H2|T2], [H3|T3]) :-
        call(Pred, H1, H2, H3),
        maplist(Pred, T1, T2, T3).
maplist(_Pred, [], [], [], []).
maplist(Pred, [H1|T1], [H2|T2], [H3|T3], [H4|T4]) :-
        call(Pred, H1, H2, H3, H4),
        maplist(Pred, T1, T2, T3, T4).

% Succeeds as many times as Goal, with N successfully bound to N0, N0+1, N0+2...
% Can also be used with N bound to get the Nth success of Goal.
enumerate(Goal, N, N0) :-
        flag(enumerate, Old, N0),
        (
            Goal,
            flag(enumerate, Current, Current+1),
            N = Current
        ;
        flag(enumerate, _, Old),
        fail).

% Count the number of successes of Goal
countsuccesses(Goal, N) :-
        flag(countsuccesses, Old, 0),
        (
            Goal,
            flag(countsuccesses, Current, Current+1),
            fail
        ;
        flag(countsuccesses, N, Old)).

% [X,Y,Z...] --> [(X,0), (Y,1), (Z,2)...]
enumerate_list([], [], Index, Index).
enumerate_list([H|T], [(H, Start)|Tail], Start, End) :-
        succ(Start, Next),
        enumerate_list(T, Tail, Next, End).


% joinlist(+Map, +List, -ResultList)
% calls Map(X,L) for all X in List.  ResultList is the concatenation of all L's.
joinlist(_, [], []).
joinlist(Map, [Head|Tail], ResultList) :-
        call(Map, Head, L1),
        joinlist(Map, Tail, L2),
        append(L1, L2, ResultList).

joinlist(_, [], [], []).
joinlist(Map, [H1|T1], [H2|T2], ResultList) :-
        call(Map, H1, H2, L1),
        joinlist(Map, T1, T2, L2),
        append(L1, L2, ResultList).

joinlist(_, [], [], [], []).
joinlist(Map, [H1|T1], [H2|T2], [H3|T3], ResultList) :-
        call(Map, H1, H2, H3, L1),
        joinlist(Map, T1, T2, T3, L2),
        append(L1, L2, ResultList).

% chainlist(+Map, +List, +Input, -Output)
% DCG chain: calls Map(X1, Input, A), Map(X2, A, B), Map(X3, B, C), ...
chainlist(_, [], IO, IO).
chainlist(Map, [Head|Tail], Input, Output) :-
        call(Map, Head, Input, Middle),
        chainlist(Map, Tail, Middle, Output).

chainlist(_, [], [], IO, IO).
chainlist(Map, [H1|T1], [H2|T2], Input, Output) :-
        call(Map, H1, H2, Input, Middle),
        chainlist(Map, T1, T2, Middle, Output).

chainlist(_, [], [], [], IO, IO).
chainlist(Map, [H1|T1], [H2|T2], [H3|T3], Input, Output) :-
        call(Map, H1, H2, H3, Input, Middle),
        chainlist(Map, T1, T2, T3, Middle, Output).
