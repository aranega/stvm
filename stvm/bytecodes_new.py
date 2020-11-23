
class ByteCodeMap(object):
    bytecodes = {}

    def execute(self, bytecode, context, vm):
        return self.bytecodes[bytecode].execute(bytecode, context, vm)

    def display(self, bytecode, context, active=False):
        try:
            return self.bytecodes[bytecode].display(bytecode, context, active)
        except KeyError:
            return "NotYet"


def bytecode(numbers, register=ByteCodeMap):
    def inner_register(cls):
        if isinstance(numbers, range):
            for i in numbers:
                register.bytecodes[i] = cls
        else:
            register.bytecodes[numbers] = cls
        return cls
    return inner_register


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
    def display(bytecode, context, active=False):
        index = bytecode - 64
        association = context.compiled_method.literals[index]
        return f"pushLitVar {association[0].as_text()}"


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
    def display(bytecode, context, active=False):
        index = bytecode - 208
        receiver = ""
        if active:
            receiver = context.peek()
            # cls_name = receiver.class_
            receiver = f"rcvr=<0x{id(receiver):X}>"
        selector = context.compiled_method.literals[index].as_text()
        return f"send {selector} {receiver}"


@bytecode(136)
class DuplicateTopStack(object):
    @staticmethod
    def execute(bytecode, context, vm):
        context.push(context.peek())
        context.pc += 1

    @staticmethod
    def display(bytecode, context, active=False):
        top = ""
        if active:
            top = context.peek()
            top = f"top=<0x{id(top):X}>"
        return f"dup {top}"


@bytecode(range(113, 116))
class PushSpecialObject(object):
    @staticmethod
    def execute(bytecode, context, vm):
        position = 2 - (bytecode - 113)
        obj = vm.memory.special_object_array[position]
        context.push(obj)
        context.pc += 1

    @staticmethod
    def display(bytecode, context, active=False):
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
