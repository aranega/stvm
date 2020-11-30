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
        context.push(context.stack[num])
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        num = bytecode - 16
        temp = ""
        if active:
            temp = context.stack[num].display()
            temp = f"tmp={temp}"
        return f"pushTempOrArg {num} {temp}"


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
            constant = f'[{constant.as_text()}]'
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
        return f"pushLitVar {association[0].display()}"


@bytecode(range(96, 104))
class PopIntoReceiverVariable(object):
    @staticmethod
    def execute(bytecode, context, vm):
        index = bytecode - 96
        receiver = context.receiver
        value = context.pop()
        context.receiver[index] = value
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        index = bytecode - 96
        val = ""
        if active:
            val = context.peek()
            val = f"value={val.display()}"
        receiver = context.receiver
        return f"popIntoRcvrInstvar {index} rcvr={receiver.display()} {val}"


@bytecode(range(104, 112))
class PopIntoTemp(object):
    @staticmethod
    def execute(bytecode, context, vm):
        index = bytecode - 104
        value = context.pop()
        context.stack[index] = value
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        index = bytecode - 104
        val = ""
        if active:
            val = context.peek()
            val = f"val={val.display()}"
        return f"popIntoTemp {index} {val}"


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


@bytecode(120)
class ReturnReceiver(object):
    @staticmethod
    def execute(bytecode, context, vm):
        context.push(context.receiver)
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        rcvr = context.receiver
        rcvr = f"rcvr={rcvr.display()}"
        return f"return receiver {rcvr}"


@bytecode(121)
class ReturnTrue(object):
    @staticmethod
    def execute(bytecode, context, vm):
        context.push(vm.memory.true)
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        return f"return true"


@bytecode(122)
class ReturnFalse(object):
    @staticmethod
    def execute(bytecode, context, vm):
        context.push(vm.memory.false)
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        return f"return false"


@bytecode(123)
class ReturnNil(object):
    @staticmethod
    def execute(bytecode, context, vm):
        context.push(vm.memory.nil)
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        return f"return nil"


@bytecode(124)
class Return(object):
    @staticmethod
    def execute(bytecode, context, vm):
        # if context.closure:
        #     context.previous_context = context.closure.previous_context
        context.pc += 1

    @classmethod
    def display(cls, bytecode, context, vm, position=None, active=False):
        res = ""
        if active:
            res = context.peek()
            res = f"ret={res.display()}"
        return f"returnTop {res}"


@bytecode(125)
class BlockReturn(object):
    @staticmethod
    def execute(bytecode, context, vm):
        ctx = context.closure.outer_context
        # cm = ctx.
        # ctx.stack[]
        context.previous.next = ctx
        context.pc += 1

    @classmethod
    def display(cls, bytecode, context, vm, position=None, active=False):
        to = ""
        if active:
            to = context.closure
            to = f"to={to.outer_context.display()}"
        return f"block return {to}"


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
            association.slots[1] = top
        elif target == 2:
            print('Cover me!')
            import ipdb; ipdb.set_trace()
        elif target == 1:  # temporary location
            context.stack[index] = top
        else:  # receiver variable
            context.receiver.slots[index] = top
            # import ipdb; ipdb.set_trace()

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


@bytecode(131)
class SingleExtendSend(object):
    display_jump = 2

    @staticmethod
    def execute(byte, context, vm):
        cm = context.compiled_method
        frmt = cm.raw_data[context.pc + 1]
        nb_args = (frmt & 0b11100000) >> 5
        index = frmt & 0b00011111
        selector = cm.literals[index]

        args = [context.pop() for _ in range(nb_args)]
        args.reverse()
        receiver = context.pop()

        compiled_method = vm.lookup(receiver.class_, selector)
        new_context = context.__class__(receiver, compiled_method, vm)
        new_context.stack[:nb_args] = args
        context.next = new_context
        context.pc += 2

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        cm = context.compiled_method
        frmt = cm.raw_data[position + 1]
        nb_args = (frmt & 0b11100000) >> 5
        index = frmt & 0b00011111
        selector = cm.literals[index].as_text()
        rcvr = args = ""
        if active:
            rcvr = context.stack[-nb_args-1]
            rcvr = f"rcvr={rcvr.display()}"
            args = [x.display() for x in context.stack[-nb_args:]]
            args = f"args={', '.join(reversed(args))}"

        return f"<%> send {selector} {rcvr} {args}"


@bytecode(132)
class DoubleExtendSend(object):
    display_jump = 3

    @staticmethod
    def execute(byte, context, vm):
        cm = context.compiled_method
        frmt = cm.raw_data[context.pc + 1]
        operation = (frmt & 0b11100000) >> 5
        index = cm.raw_data[context.pc + 2]

        if operation == 0:  # send
            import ipdb; ipdb.set_trace()
            nb_args = frmt & 0b00011111
            args = [context.pop() for _ in range(nb_args)]
            args.reverse()
            receiver = context.pop()
            selector = context.compiled_method.literals[literal_index]
            prepare_new_context(context, receiver, selector.as_text(), args=args)
        elif operation == 1:  # super send
            import ipdb; ipdb.set_trace()
        elif operation == 2:  # push receiver variable
            receiver = context.receiver
            context.push(receiver[index])
        elif operation == 3:  # push literal constant
            import ipdb; ipdb.set_trace()
        elif operation == 4:  # push literal variable
            import ipdb; ipdb.set_trace()
        elif operation == 5:  # store receiver variable
            import ipdb; ipdb.set_trace()
        elif operation == 6:  # store-pop recevier variable
            import ipdb; ipdb.set_trace()
        elif operation == 7:  # store literal variable
            import ipdb; ipdb.set_trace()
        context.pc += 3

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        action = ""
        cm = context.compiled_method
        frmt = cm.raw_data[position + 1]
        nb_args = frmt & 0b00011111
        operation = (frmt & 0b11100000) >> 5
        index = cm.raw_data[position + 2]
        if operation == 0:  # send
            action = "send"
            selector = cm.literals[index]
            args = selector.as_text()
        elif operation == 1:  # super send
            action = "super send"
            args = "#TODO"
            import ipdb; ipdb.set_trace()
        elif operation == 2:  # push receiver variable
            action = "pushRcvrInstvar"
            args = f"index={index}"
        elif operation == 3:  # push literal constant
            action = "pushConstant"
            args = f"{cm.literals[index]}"
        elif operation == 4:  # push literal variable
            action = "pushLitVar"
            args = f"unknown #TODO"
        elif operation == 5:  # store receiver variable
            action = "storeInRcvrInstvar"
            args = f"index={index} TODO"
        elif operation == 6:  # store-pop recevier variable
            action = "storePopInRcvrInstvar"
            args = f"index={index} TODO"
        elif operation == 7:  # store literal variable
            action = "storeLitVar"
            args = f"index={index} TODO"
        return f"<$> {action} {args}"


@bytecode(133)
class SuperSend(object):
    display_jump = 2

    @staticmethod
    def execute(bytecote, context, vm):
        cm = context.compiled_method
        frmt = cm.raw_data[context.pc + 1]
        nb_args = (frmt & 0b11100000) >> 5
        index = frmt & 0b00011111
        selector = cm.literals[index]
        superclass = cm.slots[cm.num_literals][1][0]

        args = [context.pop() for _ in range(nb_args)]
        args.reverse()
        receiver = context.pop()

        compiled_method = vm.lookup(superclass, selector)
        new_context = context.__class__(receiver, compiled_method, vm)
        new_context.stack[:nb_args] = args
        context.next = new_context
        context.pc += 2

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        cm = context.compiled_method
        frmt = cm.raw_data[position + 1]
        nb_args = (frmt & 0b11100000) >> 5
        index = frmt & 0b00011111
        selector = cm.literals[index].as_text()
        superclass = cm.slots[cm.num_literals][1][0]
        return f"super {selector} from={superclass.name}"


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


@bytecode(137)
class PushThisContext(object):
    @staticmethod
    def execute(bytecode, context, vm):
        ctx = context.to_smalltalk_context()
        context.push(ctx)
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        return f"push thisContext ctx={context.display()}"


@bytecode(138)
class PushOrPopIntoArray(object):
    display_jump = 2

    @staticmethod
    def execute(bytecode, context, vm):
        cm = context.compiled_method
        array_info = cm.raw_data[context.pc + 1]
        pop = (array_info & 0x80) > 0
        size = array_info & 0x7F
        array_cls = vm.memory.array
        inst = vm.allocate(array_cls, array_size=size)
        if pop:
            for i in range(size):
                inst.array[i] = context.pop()
        context.push(inst)
        context.pc += 2

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        cm = context.compiled_method
        array_info = cm.raw_data[position + 1]
        pop = (array_info & 0x80) > 0
        size = array_info & 0x7F
        mode = f"create and push array size={size}"
        if active and pop:
            stacklen = len(context.stack)
            vals = [context.stack[i].display() for i in range(stacklen-size, stacklen)]
            mode = f"create and pop/push into array size={size} values={val.display()}"
        return mode


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
            args.extend(context.stack[:nb_params])
            context.from_primitive = True
            result = execute_primitive(primitive, context, vm, *args)
            return result
        except PrimitiveFail:
            context.primitive_success = False
            # put back the parameters
            # for _ in range(len(ctx_args)):
            #     context.push(ctx_args.pop())
            context.pc += 3

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        cm = context.compiled_method
        primitive = cm.bytecodes[1:3].cast("h")[0]
        return f"primitiveCall {primitive}"


@bytecode(range(140, 143))
class PopIntoTempOfVector(object):
    display_jump = 3

    @staticmethod
    def execute(bytecode, context, vm):
        operation = bytecode - 140
        cm = context.compiled_method
        vect_index = cm.raw_data[context.pc + 2]
        temp_index = cm.raw_data[context.pc + 1]
        vector = context.stack[vect_index]
        if operation == 2:
            vector.slots[temp_index] = context.pop()
        elif operation == 1:
            vector.slots[temp_index] = context.peek()
        else:
            context.push(vector.slots[temp_index])
        context.pc += 3

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        operation = bytecode - 140
        if operation == 2:
            operation = "pop into"
        elif operation == 1:
            operation = "peekStore into"
        else:
            operation = "push from"
        cm = context.compiled_method
        vect_index = cm.raw_data[position + 2]
        temp_index = cm.raw_data[position + 1]
        return f"{operation} vector {vect_index} at {temp_index}"


@bytecode(143)
class PushClosure(object):
    display_jump = 4

    @staticmethod
    def execute(bytecode, context, vm):
        cm = context.compiled_method
        info = cm.raw_data[context.pc + 1]
        num_copied = (info & 0xF0) >> 4
        num_args = info & 0x0F

        closure_class = vm.memory.block_closure_class
        closure = vm.allocate(closure_class, array_size=num_copied)
        closure.slots[0] = context.to_smalltalk_context()
        closure.slots[1] = ImmediateInteger.create(context.pc + 4, vm.memory)
        closure.slots[2] = ImmediateInteger.create(num_args, vm.memory)
        copied = [context.pop() for i in range(num_copied)]
        # copied = reversed([context.pop() for i in range(num_copied)])
        for i, e in enumerate(copied, start=3):
            closure.slots[i] = e
        # for i in range(num_copied):
        #     closure.slots[i + 3] = context.stack[i]

        context.push(closure)
        size = int.from_bytes(cm.raw_data[context.pc + 2: context.pc + 4], byteorder="big")
        context.pc += 4 + size

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        cm = context.compiled_method
        info = cm.raw_data[position + 1]
        num_copied = (info & 0xF0) >> 4
        num_args = info & 0x0F
        size = int.from_bytes(cm.raw_data[position + 2: position + 4], byteorder="big")
        return f"closureCopy from={position + 4} to={position + size + 3} num_args={num_args} copied={num_copied}"


@bytecode(range(144, 152))
class Jump(object):
    @staticmethod
    def execute(bytecode, context, vm):
        jump_pc = bytecode - 143
        context.pc += 1
        context.pc += jump_pc

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        jump_pc = bytecode - 143
        return f"jump {jump_pc + position + 1}"


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


@bytecode(range(160, 168))
class LongJump(object):
    display_jump = 2

    @staticmethod
    def execute(bytecode, context, vm):
        shift = context.pc + ((bytecode - 160) - 4) * 256
        cm = context.compiled_method
        addr = cm.raw_data[context.pc + 1] + shift + 2
        context.pc = addr

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        shift = position + ((bytecode - 160) - 4) * 256
        cm = context.compiled_method
        addr = cm.raw_data[position + 1] + shift + 2
        return f"longJump {addr}"


@bytecode(range(168, 172))
class LongJumpTrue(object):
    display_jump = 2

    @staticmethod
    def execute(bytecode, context, vm):
        pc = context.pc
        true = vm.memory.true
        result = context.pop()
        if result is true:
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
            true = vm.memory.true
            result = context.peek()
            if result is true:
                res = "[will jump]"
            else:
                res = "[will not jump]"
        return f"jumpTrue {addr} {res}"



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
        args.reverse()
        receiver = context.pop()
        compiled_method = vm.lookup(receiver.class_, selector)
        new_context = context.__class__(receiver, compiled_method, vm)
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
                args.append(f"arg={context.stack[-i - 1].display()}>")
            args.reverse()
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
        new_context = context.__class__(receiver, compiled_method, vm)
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
        new_context = context.__class__(receiver, compiled_method, vm)
        new_context.stack[0] = arg0

        context.next = new_context
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        index = bytecode - 224
        selector = context.compiled_method.literals[index]
        args = ""
        receiver = ""
        if active:
            receiver = context.stack[-2]
            receiver = f"rcvr={receiver.display()}"
            args = context.stack[-1].display()
            args = f"arg={args}"
        return f"send {selector.as_text()} {receiver} {args}"


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
        new_context = context.__class__(receiver, compiled_method, vm)
        new_context.stack[0] = arg0
        new_context.stack[1] = arg1

        context.next = new_context
        context.pc += 1

    @staticmethod
    def display(bytecode, context, vm, position=None, active=False):
        index = bytecode - 240
        selector = context.compiled_method.literals[index]
        args = ""
        receiver = ""
        if active:
            receiver = context.stack[-3]
            receiver = f"rcvr={receiver.display()}"
            args = context.stack[-2].display(), context.stack[-1].display()
            args = f"args={', '.join(args)}"
        return f"send {selector.as_text()} {receiver} {args}"
