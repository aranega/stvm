from .vm import Continuate, Finish, VM, Context, vmobject
from .primitives import execute_primitive, build_int, PrimitiveFail


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


@register_bytecode([[96, 103]])
class PopIntoReceiverVariable(Bytecode):
    def execute(self, context):
        variable_index = self.opcode - 96
        value = context.pop()
        context.receiver.obj.instvars[variable_index] = value.obj
        context.pc += 1


@register_bytecode([[104, 111]])
class PopIntoTemp(Bytecode):
    def execute(self, context):
        temp_index = self.opcode - 104
        value = context.pop()
        context.temporaries[temp_index] = value
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
        lookup_cls = context.compiled_method.from_cls

        compiled_method = lookup_cls.superclass.lookup(selector)
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


@register_bytecode([138])
class PushOrPopIntoArray(Bytecode):
    def execute(self, context):
        pc = context.pc
        array_info = context.compiled_method.obj.bytecode[pc + 1]
        pop = (array_info & 0x80) > 0
        size = array_info & 0x7F
        array_cls = vmobject(context.vm.mem.array)
        new_context = prepare_new_context(context, array_cls, "new:", args=[size])
        new_context.execute()
        if pop:
            result = context.peek()
            for i in range(size):
                result.array[i] = context.pop().obj
            import ipdb; ipdb.set_trace()
        context.pc += 2


@register_bytecode([139])
class CallPrimitive(Bytecode):
    def execute(self, context):
        try:
            pc = context.pc
            primitive_number = int.from_bytes(context.compiled_method.obj.bytecode[pc + 1 : pc + 3], 'little')
            result = execute_primitive(primitive_number, context)
            context.pc += 3
            return vmobject(result)
        except PrimitiveFail:
            context.pc += 3


@register_bytecode([142])
class PopIntoTempInTempVector(Bytecode):
    def execute(self, context):
        pc = context.pc
        bytecodes = context.compiled_method.obj.bytecode
        tempvect_index = bytecodes[pc + 2]
        tempvect = context.temporaries[tempvect_index]
        value = context.pop()
        temp_index = bytecodes[pc + 1]
        tempvect.obj.array[temp_index] = value.obj

        context.pc += 3


@register_bytecode([143])
class PushClosure(Bytecode):
    def execute(self, context):
        pc = context.pc
        block_info = context.compiled_method.obj.bytecode[pc + 1]
        num_copied = (block_info & 0xF0) >> 4
        num_args = block_info & 0x0F
        block_size = int.from_bytes(context.compiled_method.obj.bytecode[pc + 2 : pc + 4], 'big')

        copied = [context.pop() for i in range(num_copied)]

        extract_block = context.compiled_method.obj.extract_block
        block = extract_block(copied, num_args, pc + 4, block_size, context)
        block.home_context = context
        context.push(vmobject(block))

        context.pc += 4 + block_size


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


@register_bytecode([180])
class PerformInfEqual(Bytecode):
    def execute(self, context):
        arg = context.pop()
        receiver = context.pop()
        prepare_new_context(context, receiver, '<=', args=[arg])
        context.pc += 1
        raise Continuate()


@register_bytecode([182])
class PerformEqual(Bytecode):
    def execute(self, context):
        arg = context.pop()
        receiver = context.pop()
        prepare_new_context(context, receiver, '=', args=[arg])
        context.pc += 1
        raise Continuate()


@register_bytecode([192])
class PerformAt(Bytecode):
    def execute(self, context):
        arg = context.pop()
        receiver = context.pop()
        prepare_new_context(context, receiver, 'at:', args=[arg])
        context.pc += 1
        raise Continuate()


@register_bytecode([194])
class PerformSize(Bytecode):
    def execute(self, context):
        receiver = context.pop()
        prepare_new_context(context, receiver, 'size')
        context.pc += 1
        raise Continuate()


@register_bytecode([198])
class PerformDoubleEqual(Bytecode):
    def execute(self, context):
        arg = context.pop()
        receiver = context.pop()
        prepare_new_context(context, receiver, '==', args=[arg])
        context.pc += 1
        raise Continuate()


@register_bytecode([201])
class PerformValue(Bytecode):
    def execute(self, context):
        closure = context.pop()
        prepare_new_context(context, closure, 'value')
        context.pc += 1
        raise Continuate()


@register_bytecode([202])
class PerformValueWithArgs(Bytecode):
    def execute(self, context):
        args = context.pop()
        closure = context.pop()
        prepare_new_context(context, closure, 'value:', args=[args])
        context.pc += 1
        raise Continuate()


@register_bytecode([203])
class PerformDo(Bytecode):
    def execute(self, context):
        block = context.pop()
        receiver = context.pop()
        prepare_new_context(context, receiver, 'do:', args=[block])
        context.pc += 1
        raise Continuate()


@register_bytecode([204])
class PerformNew(Bytecode):
    def execute(self, context):
        cls = context.pop()
        print("Perform new for", cls.obj[6].as_text())
        prepare_new_context(context, cls, 'new')
        context.pc += 1
        raise Continuate()


@register_bytecode([205])
class PerformNewWithArg(Bytecode):
    def execute(self, context):
        arg = context.pop()
        cls = context.pop()
        print("Perform new: for", cls)
        prepare_new_context(context, cls, 'new:', args=[arg])
        context.pc += 1
        raise Continuate()


def prepare_new_context(context, receiver, selector, args=None):
    compiled_method = receiver.class_.lookup_byname(selector)
    # if compiled_method is None:
    #     compiled_method = receiver.class_.lookup_byname('doesNotUnderstand:')
    if compiled_method is None:
        print('Method', selector, 'not found')
        import ipdb; ipdb.set_trace()

    new_context = Context(
        compiled_method=compiled_method,
        receiver=receiver,
        previous_context=context,
        args=args
    )
    return new_context


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
        selector = context.compiled_method.literals[literal_index]
        arg = context.pop()
        receiver = context.pop()
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
