% This file defines combination of instructions, or more precisely instruction
% modes, that should be produced as a single larger instruction with its
% own bytecode.  There are about 73 basic instruction modes, so this leaves
% room for 182 extra combined instructions.  For example:

%% mode_combine([s_push(0), immed(char)]).
%% mode_combine([s_push(0), immed(char), cmplt]).
%% mode_combine([s_push(0), immed(char), cmplt, jcondfar(long)]).

% See py-utils/ivmoptimize.py for a way to generate automatically the 182 best
% combinations for your own program.  Optimizing Psyco/IVM in this way for a
% specific program can make it run quite faster.
