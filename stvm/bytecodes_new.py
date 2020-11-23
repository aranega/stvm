from primitives_new import execute_primitive, PrimitiveFail
from spurobjects.immediate import ImmediateInteger


class ByteCodeMap(object):
    bytecodes = {}

    def get(self, bytecode):
        return self.bytecodes.get(bytecode, NotYet)

    def execute(self, bytecode, context, vm):
        return self.get(bytecode).execute(bytecode, context, vm)

    def display(self, bytecode, context, vm, position=None, active=False):
        return self.get(bytecode).display(bytecode, context, vm, position, active)


def bytecode(numbers, register=ByteCodeMap):
    def inner_register(cls):
        if isinstance(numbers, range):
            for i in numbers:
                register.bytecodes[i] = cls
        else:
            register.bytecodes[numbers] = cls
        if not getattr(cls, "display_jump", False):
            cls.display_jump = 1
        return cls
    return inner_register


class NotYet(object):
    display_jump = 1
    @staticmethod
    def execute(bytecode, context, vm):
        raise NotImplementedError(f"Bytecode ({bytecode}) not yet implemented")

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        return f"NotYet"


@bytecode(range(0, 16))
class PushReceiverVariable(object):
    @staticmethod
    def execute(bytecode, context, vm):
        index = bytecode
        receiver = context.receiver
        value = receiver.slots[index]
        context.push(value)
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        index = bytecode
        value = ""
        if active:
            receiver = context.receiver
            value = receiver.slots[index]
            value = f"val={value.display()}"
        return f"pushRcvrInstvar {index} {value}"


@bytecode(range(16, 32))
class PushTemp(object):
    @staticmethod
    def execute(bytecode, context, vm):
        num = bytecode - 16
        context.push(context.temps[num])
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        num = bytecode - 16
        temp = ""
        if active:
            temp = context.temps[num].display()
            temp = f"tmp={temp}"
        return f"pushTemp {num} {temp}"


@bytecode(range(32, 64))
class PushLiteralConstant(object):
    @staticmethod
    def execute(bytecode, context, vm):
        index = bytecode - 32
        constant = context.compiled_method.literals[index]
        context.push(constant)
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        index = bytecode - 32
        constant = context.compiled_method.literals[index]
        try:
            constant = f'"{constant.as_text()}"'
        except Exception:
            constant = constant.display()
        return f"pushConstant {constant} "


@bytecode(range(64, 96))
class PushLiteralVariable(object):
    @staticmethod
    def execute(bytecode, context, vm):
        index = bytecode - 64
        association = context.compiled_method.literals[index]
        variable = association[1]
        context.push(variable)
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        index = bytecode - 64
        association = context.compiled_method.literals[index]
        if isinstance(association[0], int):
            import ipdb; ipdb.set_trace()

        return f"pushLitVar {association[0].display()}"


@bytecode(112)
class PushReceiver(object):
    @staticmethod
    def execute(bytecode, context, vm):
        context.push(context.receiver)
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        receiver = ""
        if active:
            receiver = context.receiver
            receiver = receiver.display()
        return f"self {receiver}"


@bytecode(range(113, 116))
class PushSpecialObject(object):
    @staticmethod
    def execute(bytecode, context, vm):
        position = 2 - (bytecode - 113)
        obj = vm.memory.special_object_array[position]
        context.push(obj)
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        position = 2 - (bytecode - 113)
        if position == 0:
            obj = "nil"
        elif position == 1:
            obj = "false"
        elif position == 2:
            obj = "true"
        else:
            obj = vm.memory.special_object_array[position].name
        return f"pushConstant {obj}"


@bytecode(range(116, 120))
class PushInt(object):
    @staticmethod
    def execute(bytecode, context, vm):
        value = bytecode - 117
        immediate = ImmediateInteger.create(value, vm.memory)
        context.push(immediate)
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        value = bytecode - 117
        return f"pushInt {value}"


@bytecode(121)
class ReturnTrue(object):
    @staticmethod
    def execute(bytecode, context, vm):
        context.push(vm.memory.true)

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        return f"return true"


@bytecode(122)
class ReturnFalse(object):
    @staticmethod
    def execute(bytecode, context, vm):
        context.push(vm.memory.false)

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        return f"return false"


@bytecode(123)
class ReturnNil(object):
    @staticmethod
    def execute(bytecode, context, vm):
        context.push(vm.memory.nil)

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        return f"return nil"


@bytecode(124)
class Return(object):
    @staticmethod
    def execute(bytecode, context, vm):
        if context.outer_context:
            context.previous_context = context.outer_context.previous_context

    @classmethod
    def display(cls, bytecode, context, vm, position=None, active=False):
        res = ""
        if active:
            res = context.peek()
            res = f"ret={res.display()}"
        return f"returnTop {res}"


@bytecode(range(129, 131))
class OperationLongForm(object):
    display_jump = 2
    operation = ['peek', 'pop']

    @classmethod
    def execute(cls, bytecode, context, vm):
        cm = context.compiled_method
        target_encoded = cm.raw_data[context.pc + 1]
        target = (target_encoded & 0xC0) >> 6
        index = target_encoded & 0x3F

        label = cls.operation[bytecode - 129]
        top = getattr(context, label)()

        if target == 3:  # into literal variable
            association = cm.literals[index]
            association.instvars[1] = top
        elif target == 2:
            print('Cover me!')
            import ipdb; ipdb.set_trace()
        elif target == 1:  # temporary location
            context.temps[index] = top
        else:  # receiver variable
            context.receiver.instvars[index] = top
        context.pc += 2

    @classmethod
    def display(cls, bytecode, context, vm, position=None, active=False):
        label = cls.operation[bytecode - 129]
        cm = context.compiled_method
        target_encoded = cm.raw_data[position + 1]
        target = (target_encoded & 0xC0) >> 6
        index = target_encoded & 0x3F
        if target == 3:
            label += f"IntoLit {index}"
        elif target == 2:
            label += f"Coverme {index}"
        elif target == 1:
            label += f"IntoTemp {index}"
        else:
            label += f"IntoRcvrVar {index}"
        if active:
            top = context.peek()
            label += f" val={top.display()}"
        return f"{label}"


@bytecode(135)
class PopStackTop(object):
    @staticmethod
    def execute(bytecode, context, vm):
        context.pop()
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        return "pop"


@bytecode(136)
class DuplicateTopStack(object):
    @staticmethod
    def execute(bytecode, context, vm):
        context.push(context.peek())
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        top = ""
        if active:
            top = context.peek()
            top = top.display()
        return f"dup {top}"


@bytecode(139)
class CallPrimitive(object):
    display_jump = 3

    @staticmethod
    def execute(bytecode, context, vm):
        cm = context.compiled_method
        current_pc = context.pc
        try:
            pc = context.pc
            primitive = cm.raw_data[pc + 1: pc + 3].cast("h")[0]
            nb_params = cm.num_args
            args = [context.receiver]
            for i in range(nb_params):
                args.append(context.stack[-i - 1])
            context.from_primitive = True
            result = execute_primitive(primitive, context, vm, *args)
            context.push(result)
            return result
        except PrimitiveFail:
            context.primitive_success = False
            context.pc += 3

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        cm = context.compiled_method
        primitive = cm.bytecodes[1:3].cast("h")[0]
        return f"primitiveCall {primitive}"


@bytecode(range(152, 160))
class JumpFalse(object):
    @staticmethod
    def execute(bytecode, context, vm):
        if context.pop() is vm.memory.false:
            addr = (bytecode - 151) + 1
            context.pc += addr
            return
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        addr = position + (bytecode - 151) + 1
        result = ""
        if active:
            false = vm.memory.false
            if context.peek() is false:
                result = "[will jump]"
            else:
                result = "[will not jump]"
        return f"jumpFalse {addr} {result}"


@bytecode(range(172, 176))
class LongJumpFalse(object):
    display_jump = 2

    @staticmethod
    def execute(bytecode, context, vm):
        pc = context.pc
        false = vm.memory.false
        result = context.pop()
        if result is false:
            cm = context.compiled_method
            addr = cm.raw_data[pc + 1]
            context.pc += addr + 2
            return
        context.pc += 2

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        cm = context.compiled_method
        addr = cm.raw_data[position + 1] + position + 2
        res = ""
        if active:
            false = vm.memory.false
            result = context.peek()
            if result is false:
                res = "[will jump]"
            else:
                res = "[will not jump]"
        return f"jumpFalse {addr} {res}"


@bytecode(range(176, 208))
class SendSpecialMessage(object):
    @staticmethod
    def execute(bytecode, context, vm):
        pos = (bytecode - 176) * 2
        selector = vm.memory.special_symbols[pos]

        nb_params = vm.memory.special_symbols[pos + 1]
        args = []
        for i in range(nb_params):
            args.append(context.pop())

        receiver = context.pop()
        compiled_method = vm.lookup(receiver.class_, selector)
        new_context = context.__class__(receiver, compiled_method)
        new_context.stack[:nb_params] = args
        context.next = new_context
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        pos = (bytecode - 176) * 2
        selector = vm.memory.special_symbols[pos].as_text()

        params = ""
        if active:
            nb_params = vm.memory.special_symbols[pos + 1]
            args = []
            for i in range(nb_params):
                args.append(f"arg[{i}]={context.stack[-i - 1].display()}>")
            args = ", ".join(args)
            receiver = context.stack[-nb_params - 1]
            receiver = f"rcvr={receiver.display()}"
            params = f"{receiver} {args}"

        return f"send {selector} {params}"


@bytecode(range(208, 224))
class Send0ArgSelector(object):
    @staticmethod
    def execute(bytecode, context, vm):
        index = bytecode - 208
        receiver = context.pop()
        selector = context.compiled_method.literals[index]
        compiled_method = vm.lookup(receiver.class_, selector)
        new_context = context.__class__(receiver, compiled_method)
        context.next = new_context
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        index = bytecode - 208
        receiver = ""
        if active:
            receiver = context.peek()
            # cls_name = receiver.class_
            receiver = f"rcvr={receiver.display()}"
        selector = context.compiled_method.literals[index].as_text()
        return f"send {selector} {receiver}"


@bytecode(range(224, 240))
class Send1ArgSelector(object):
    @staticmethod
    def execute(bytecode, context, vm):
        index = bytecode - 224
        arg0 = context.pop()
        receiver = context.pop()
        selector = context.compiled_method.literals[index]
        compiled_method = vm.lookup(receiver.class_, selector)
        new_context = context.__class__(receiver, compiled_method)
        new_context.stack[0] = arg0

        context.next = new_context
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        index = bytecode - 224
        selector = context.compiled_method.literals[index]
        args = ""
        if active:
            receiver = context.stack[-2]
            receiver = f"rcvr={receiver.display()}"
            args = context.stack[-1].display()
            args = f"arg={args}"
        return f"send {selector.as_text()} {args}"


@bytecode(range(240, 256))
class Send2ArgSelector(object):
    @staticmethod
    def execute(bytecode, context, vm):
        index = bytecode - 240
        arg1 = context.pop()
        arg0 = context.pop()
        receiver = context.pop()
        selector = context.compiled_method.literals[index]
        compiled_method = vm.lookup(receiver.class_, selector)
        new_context = context.__class__(receiver, compiled_method)
        new_context.stack[0] = arg0
        new_context.stack[1] = arg1

        context.next = new_context
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        index = bytecode - 240
        selector = context.compiled_method.literals[index]
        args = ""
        if active:
            receiver = context.stack[-3]
            receiver = f"rcvr={receiver.display()}"
            args = context.stack[-1].display(), context.stack[-2].display()
            args = f"args={','.join(args)}"
        return f"send {selector.as_text()} {args}"
