#include "ipyencoding.h"
#include "../pycodegen.h"


DEFINEFN
code_t* decref_dealloc_calling(code_t* code, PsycoObject* po, reg_t rg,
                               destructor fn)
{
  code_t* code_origin;
  int save_eax, save_ecx, save_edx;
  reg_t last_reg;
  DEC_OB_REFCNT_NZ(rg);
  extra_assert(offsetof(PyObject, ob_type) < 128);
  extra_assert(offsetof(PyTypeObject, tp_dealloc) < 128);
  code[0] = 0x75;          /* JNZ rel8 */
  code += 2;
  code_origin = code;
  if (COMPACT_ENCODING) {
    save_eax = REG_NUMBER(po, REG_386_EAX) != NULL;
    save_ecx = REG_NUMBER(po, REG_386_ECX) != NULL;
    save_edx = REG_NUMBER(po, REG_386_EDX) != NULL;
    last_reg = REG_386_EAX;
    if (save_eax) PUSH_REG(REG_386_EAX);
    if (save_ecx) { PUSH_REG(REG_386_ECX); last_reg = REG_386_ECX; }
    if (save_edx) { PUSH_REG(REG_386_EDX); last_reg = REG_386_EDX; }
    PUSH_REG(rg);
  }
  else {
    CODE_FOUR_BYTES(code,                                                     
            PUSH_REG_INSTR(REG_386_EAX),
            PUSH_REG_INSTR(REG_386_ECX),
            PUSH_REG_INSTR(REG_386_EDX),
            PUSH_REG_INSTR(rg));
    code += 4;
  }
  if (fn == NULL) {
    code[0] = 0x8B;          /* MOV EAX, [reg+ob_type] */
    code[1] = 0x40 | (rg);
    CODE_FOUR_BYTES(code+2,
            offsetof(PyObject, ob_type),
            0xFF,          /* CALL [EAX+tp_dealloc] */
            0x50,
            offsetof(PyTypeObject, tp_dealloc));
    code += 6;
  }
  else {
    code[0] = 0xE8;    /* CALL */
    code += 5;
    *(long*)(code-4) = (code_t*)(fn) - code;
  }
  if (COMPACT_ENCODING) {
    POP_REG(last_reg);  /* pop argument back */
    if (save_edx) POP_REG(REG_386_EDX);
    if (save_ecx) POP_REG(REG_386_ECX);
    if (save_eax) POP_REG(REG_386_EAX);
  }
  else {
    CODE_FOUR_BYTES(code,
            POP_REG_INSTR(REG_386_EDX),
            POP_REG_INSTR(REG_386_EDX),
            POP_REG_INSTR(REG_386_ECX),
            POP_REG_INSTR(REG_386_EAX));
    code += 4;
  }
  extra_assert(code-code_origin < 128);
  code_origin[-1] = (code_t)(code-code_origin);
  return code;
}

DEFINEFN
void decref_create_new_ref(PsycoObject* po, vinfo_t* w)
{
	/* we must Py_INCREF() the object */
	BEGIN_CODE
	if (is_compiletime(w->source))
		INC_KNOWN_OB_REFCNT((PyObject*)
				    CompileTime_Get(w->source)->value);
	else {
		/* 'w' is in a register because of write_array_item() */
		extra_assert(!RUNTIME_REG_IS_NONE(w));
		INC_OB_REFCNT(RUNTIME_REG(w));
	}
	END_CODE
}

DEFINEFN
bool decref_create_new_lastref(PsycoObject* po, vinfo_t* w)
{
	bool could_eat = eat_reference(w);
	if (!could_eat) {
		/* in this case we must Py_INCREF() the object */
		BEGIN_CODE
		if (is_compiletime(w->source))
			INC_KNOWN_OB_REFCNT((PyObject*)
					    CompileTime_Get(w->source)->value);
		else {
			/* 'w' is in a register because of write_array_item() */
			extra_assert(!RUNTIME_REG_IS_NONE(w));
			INC_OB_REFCNT(RUNTIME_REG(w));
		}
                END_CODE
	}
	return could_eat;
}
