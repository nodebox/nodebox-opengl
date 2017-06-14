#include "ivm-insns.h"


#define setlatestopcode(opcode)   (*code = (opcode))
#define INSN_EMIT_opcode(opcode)  (*code++ = (opcode))
#define INSN_EMIT_modified_opcode(opcode, totalargs)                    \
                                  (code[-((int)(totalargs))-1] = (opcode))

#define bytecode_size(T)      sizeof(T)
#define INSN_EMIT_void(arg)   do { /*nothing*/ } while (0)
#define INSN_EMIT_byte(arg)   (*code++ = (code_t)(arg))
#define INSN_EMIT_char(arg)   (*code++ = (code_t)(arg))
#define INSN_EMIT_int(arg)    (*(int*)code = (int)(arg), code += sizeof(int))
#define INSN_EMIT_word_t(arg) (*(word_t*)code=(word_t)(arg),code+=sizeof(word_t))
#define INSN_EMIT_placeholder_byte(ppbyte)  (*(ppbyte)=code++)
#define INSN_EMIT_placeholder_long(ppword)  (*(ppword)=(word_t*)code,        \
                                        code+=sizeof(word_t))


#include "prolog/insns-igen.i"
