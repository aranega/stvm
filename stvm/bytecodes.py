from .vm import Continuate, Finish, VM, Context, vmobject
from .image_reader32 import ImmediateInteger


def register_bytecode(l):
    result = []
    for x in l:
        if isinstance(x, list):
            result.extend(range(x[0], x[1] + 1))
        else:
            result.append(x)

    def inner_register(cls):
        for i in result:
            VM.bytecode_map[i] = cls
        return cls

    return inner_register


class Bytecode(object):
    def __init__(self, opcode):
        self.opcode = opcode

    def execute(self, context):
        pass


@register_bytecode([[0, 15]])
class PushReceiverVariable(Bytecode):
    def execute(self, context):
        var_number = self.opcode
        receiver = context.receiver
        context.push(receiver.instvars[var_number])
        context.pc += 1


@register_bytecode([[16, 31]])
class PushTemp(Bytecode):
    def execute(self, context):
        temp_number = self.opcode - 16
        context.push(context.temporaries[temp_number])
        context.pc += 1


@register_bytecode([[32, 63]])
class PushLiteralConstant(Bytecode):
    def execute(self, context):
        literal = self.opcode - 32
        context.push(literal)
        context.pc += 1


@register_bytecode([[64, 95]])
class PushLiteralVariable(Bytecode):
    def execute(self, context):
        literal_index = self.opcode - 64
        literal_association = context.compiled_method.literals[literal_index]
        context.push(literal_association.instvars[1])
        context.pc += 1


class PushThisContext(Bytecode):
    def execute(self, context):
        context.push(context)
        context.pc += 1


@register_bytecode([112])
class PushReceiver(Bytecode):
    def execute(self, context):
        context.push(context.receiver)
        context.pc += 1


@register_bytecode([[113, 115]])
class PushSpecialObject(Bytecode):
    def execute(self, context):
        position = 3 - (self.opcode - 113)
        obj = context.vm.mem.special_object_array[position]
        context.push(obj)
        context.pc += 1


def build_int(value, memory):
    immediate = ImmediateInteger(memory=memory)
    immediate.value = value
    value <<= 1
    value &= 0xFFFFFFFE
    immediate.address = value
    return immediate


@register_bytecode([[116, 119]])
class PushInt(Bytecode):
    def execute(self, context):
        value = self.opcode - 117
        immediate = build_int(value, context.vm.mem)
        context.push(vmobject(immediate))
        context.pc += 1


@register_bytecode([120])
class ReturnReceiver(Bytecode):
    def execute(self, context):
        return context.receiver


@register_bytecode([124])
class Return(Bytecode):
    def execute(self, context):
        print("Result", context.peek())
        raise Finish


@register_bytecode([135])
class PopStackTop(Bytecode):
    def execute(self, context):
        context.pop()
        context.pc += 1


@register_bytecode([136])
class DuplicateTopStack(Bytecode):
    def execute(self, context):
        context.push(context.peek())
        context.pc += 1


@register_bytecode([139])
class Nop(Bytecode):
    def execute(self, context):
        context.pc += 1


def default_primitive(context, selector):
    receiver = context.pop()
    arg = context.pop()
    compiled_method = receiver.class_.lookup_byname(selector)
    new_context = Context(
        compiled_method=compiled_method,
        receiver=receiver,
        previous_context=context,
        args=[arg],
    )

    context.pc += 1
    raise Continuate()


@register_bytecode([144, 151])
class Jump(Bytecode):
    def execute(self, context):
        jump_pc = self.opcode - 143
        context.pc += jump_pc


@register_bytecode([152, 159])
class JumpFalse(Bytecode):
    def execute(self, context):
        result = context.pop()
        if result.is_false:
            jump_pc = self.opcode - 151
            context.pc += jump_pc
        else:
            context_pc += 2


@register_bytecode([160, 163])
class LongJumpBackward(Bytecode):
    def execute(self, context):
        shift = (self.opcode - 160) * 256
        compiled_method = context.compiled_method
        jump_pc = compiled_method.raw_bytecode[context.pc + 1] + shift - 1
        context.pc -= jump_pc


@register_bytecode([164, 167])
class LongJumpForward(Bytecode):
    def execute(self, context):
        shift = (self.opcode - 164) * 256
        compiled_method = context.compiled_method
        jump_pc = compiled_method.raw_bytecode[context.pc + 1] + shift
        context.pc += jump_pc


@register_bytecode([[168, 171]])
class LongJumpTrue(Bytecode):
    def execute(self, context):
        result = context.pop()
        if result.is_true:
            shift = (self.opcode - 168) * 256
            compiled_method = context.compiled_method
            jump_pc = compiled_method.raw_bytecode[context.pc + 1] + shift
            context.pc += jump_pc
        else:
            context.pc += 2


@register_bytecode([172, 175])
class LongJumpFalse(Bytecode):
    def execute(self, context):
        result = context.pop()
        if result.is_false:
            shift = (self.opcode - 172) * 256
            compiled_method = context.compiled_method
            jump_pc = compiled_method.raw_bytecode[context.pc + 1] + shift
            context.pc += jump_pc
        else:
            context.pc += 2


@register_bytecode([176])
class PerformPlus(Bytecode):
    def execute(self, context):
        op1 = context.pop()
        op2 = context.pop()
        res = build_int(op1.obj.value + op2.obj.value, context.vm.mem)
        context.push(vmobject(res))
        print("    == ", res.value)
        context.pc += 1


@register_bytecode([178])
class PerformInf(Bytecode):
    def execute(self, context):
        receiver = context.pop()
        arg = context.pop()
        compiled_method = receiver.class_.lookup_byname("<")
        new_context = Context(
            compiled_method=compiled_method,
            receiver=receiver,
            previous_context=context,
            args=[arg],
        )

        context.pc += 1
        raise Continuate()


@register_bytecode([198])
class PerformDoubleTilde(Bytecode):
    def execute(self, context):
        receiver = context.pop()
        arg = context.pop()
        if receiver is not arg:
            context.push(context.vm.mem.true)
        else:
            context.push(context.vm.mem.false)
        context.pc += 1


@register_bytecode([204])
class PerformNew(Bytecode):
    def execute(self, context):
        cls = context.pop()
        print("Perform new for", cls)
        inst = context.vm.memory_allocator.allocate(cls)
        context.push(inst)
        context.pc += 1


@register_bytecode([[208, 223]])
class SendSelector(Bytecode):
    def execute(self, context):
        literal_index = self.opcode - 208
        receiver = context.pop()
        selector = context.compiled_method.literals[literal_index]
        compiled_method = receiver.class_.lookup(selector)
        new_context = Context(
            compiled_method=compiled_method, receiver=receiver, previous_context=context
        )

        context.pc += 1
        raise Continuate()
