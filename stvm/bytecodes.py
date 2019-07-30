from .vm import Continuate, Finish, VM, Context, vmobject
from .primitives import execute_primitive, build_int


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
        result = context.pop()
        print("Result", result)
        return result


@register_bytecode([[129, 130]])
class OperationLongForm(Bytecode):
    operation = ['peek', 'pop']
    def execute(self, context):
        compiled_method = context.compiled_method
        target_encoded = compiled_method.raw_bytecode[context.pc + 1]
        target = (target_encoded & 0xC0) >> 6
        index = target_encoded & 0x3F
        value = getattr(context, self.operation[self.opcode - 129])()
        if target == 3:  # into literal variable
            literal_association = context.compiled_method.literals[index]
            literal_association.instvars[1] = value.obj
        elif target == 2:
            print('Cover me!')
            import ipdb; ipdb.set_trace()
        elif target == 1:  # temporary location
            context.temporaries[index] = value
        else:  # receiver variable
            context.receiver.obj.instvars[index] = value.obj
        context.pc += 2


@register_bytecode([133])
class SuperSend(Bytecode):
    def execute(self, context):
        frmt = context.compiled_method.obj.bytecode[context.pc + 1]
        literal_index = frmt & 0xF0 >> 4
        nb_args = frmt & 0xF
        args = []
        for i in range(nb_args):
            args = context.pop()
        receiver = context.pop()
        selector = context.compiled_method.literals[literal_index]

        compiled_method = receiver.class_.superclass.lookup(selector)
        new_context = Context(
            compiled_method=compiled_method, receiver=receiver, previous_context=context, args=args
        )
        context.pc += 2
        raise Continuate()


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
class CallPrimitive(Bytecode):
    def execute(self, context):
        pc = context.pc
        primitive_number = int.from_bytes(context.compiled_method.obj.bytecode[pc + 1 : pc + 3], 'little')
        result = execute_primitive(primitive_number, context)
        context.pc += 3
        return vmobject(result)


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


@register_bytecode([[144, 151]])
class Jump(Bytecode):
    def execute(self, context):
        jump_pc = self.opcode - 143
        context.pc += jump_pc


@register_bytecode([[152, 159]])
class JumpFalse(Bytecode):
    def execute(self, context):
        result = context.pop()
        if result.is_false:
            jump_pc = self.opcode - 151
            context.pc += jump_pc
        else:
            context.pc += 2


@register_bytecode([[160, 163]])
class LongJumpBackward(Bytecode):
    def execute(self, context):
        shift = (self.opcode - 160) * 256
        compiled_method = context.compiled_method
        jump_pc = compiled_method.raw_bytecode[context.pc + 1] + shift - 1
        context.pc -= jump_pc


@register_bytecode([[164, 167]])
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


@register_bytecode([[172, 175]])
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
        arg = context.pop()
        receiver = context.pop()
        prepare_new_context(context, receiver, '+', args=[arg])
        context.pc += 1
        raise Continuate()


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


@register_bytecode([198])
class PerformDoubleEqual(Bytecode):
    def execute(self, context):
        arg = context.pop()
        receiver = context.pop()
        prepare_new_context(context, receiver, '==', args=[arg])
        context.pc += 1
        raise Continuate()


@register_bytecode([204])
class PerformNew(Bytecode):
    def execute(self, context):
        cls = context.pop()
        print("Perform new for", cls)
        # default_execute(context, cls, 'new')
        prepare_new_context(context, cls, 'basicNew')
        # inst = context.vm.memory_allocator.allocate(cls)
        # prepare_new_context(context, inst, 'initialize')
        context.pc += 1
        raise Continuate()


def prepare_new_context(context, receiver, selector, args=None):
    compiled_method = receiver.class_.lookup_byname(selector)
    new_context = Context(
        compiled_method=compiled_method,
        receiver=receiver,
        previous_context=context,
        args=args
    )


@register_bytecode([[208, 223]])
class Send0ArgSelector(Bytecode):
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


@register_bytecode([[224, 239]])
class Send1ArgSelector(Bytecode):
    def execute(self, context):
        literal_index = self.opcode - 224
        arg = context.pop()
        receiver = context.pop()
        selector = context.compiled_method.literals[literal_index]
        compiled_method = receiver.class_.lookup(selector)
        new_context = Context(
            compiled_method=compiled_method, receiver=receiver, previous_context=context, args=[arg]
        )
        print('Preparing', selector.as_text(), 'for execution')
        context.pc += 1
        raise Continuate()


@register_bytecode([[240, 255]])
class Send2ArgSelector(Bytecode):
    def execute(self, context):
        literal_index = self.opcode - 240
        arg1 = context.pop()
        arg2 = context.pop()
        receiver = context.pop()
        selector = context.compiled_method.literals[literal_index]
        compiled_method = receiver.class_.lookup(selector)
        new_context = Context(
            compiled_method=compiled_method, receiver=receiver, previous_context=context, args=[arg1, arg]
        )

        context.pc += 1
        raise Continuate()
