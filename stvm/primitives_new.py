import time
import struct
from spurobjects.immediate import ImmediateInteger, ImmediateFloat


primitives = {}


class PrimitiveFail(Exception):
    pass


def execute_primitive(number, context, vm, *args, **kwargs):
    memory = vm.memory
    try:
        result = primitives[number](args[0], *args[1:], context=context, vm=vm, **kwargs)
        return python2st(result, memory)
    except Exception as e:
        if number != 83:
            raise PrimitiveFail
        raise e


def st2python(obj, memory):
    if obj is memory.true:
        return True
    elif obj is memory.false:
        return False
    elif obj is memory.nil:
        return None
    return obj


def python2st(obj, memory):
    if obj is True:
        return memory.true
    if obj is False:
        return memory.false
    if obj is None:
        return memory.nil
    return obj


def primitive(numbers):
    def inner_register(fun):
        if isinstance(numbers, range):
            for i in numbers:
                primitives[i] = fun
        else:
            primitives[numbers] = fun
        return fun
    return inner_register


@primitive(1)
def plus(a, b, context, vm):
    return a.__class__.create(a.value + b.value, vm.memory)


@primitive(2)
def minus(a, b, context, vm):
    return a.__class__.create(a.value - b.value, vm.memory)


@primitive(3)
def less(a, b, context, vm):
    return a.value < b.value


@primitive(4)
def less(a, b, context, vm):
    return a.value > b.value


@primitive(5)
def lessOrEqual(a, b, context, vm):
    return a.value <= b.value


@primitive(6)
def greaterOrEqual(a, b, context, vm):
    return a.value >= b.value


@primitive(8)
def diff(a, b, context, vm):
    return a.value != b.value


@primitive(9)
def mult(a, b, context, vm):
    return a.__class__.create(a.value * b.value, vm.memory)


@primitive(10)
def div(a, b, context, vm):
    if a.value % b.value != 0:
        raise PrimitiveFail('not divisible')
    return a.__class__.create(a.value // b.value, vm.memory)


@primitive(11)
def mod(a, b, context, vm):
    return a.__class__.create(a.value % b.value, vm.memory)


@primitive(12)
def divRound(a, b, context, vm):
    return a.__class__.create(a.value // b.value, vm.memory)


@primitive(13)
def quo(a, b, context, vm):
    return a.__class__.create(a.value // b.value, vm.memory)


@primitive(14)
def bitand(a, b, context, vm):
    res = a.value & b.value
    res = a.__class__.create(res, vm.memory)
    return res


@primitive(17)
def bitshift(self, shift, context, vm):
    if shift.value < 0:
        res = self.value >> (-shift.value)
    else:
        res = self.value << shift.value
    res = self.__class__.create(res, vm.memory)
    return res


@primitive(40)
def smallintAsFloat(self, context, vm):
    return ImmediateFloat.create(self, vm.memory)



@primitive(61)
def at_put(self, at, val, context, vm):
    self[at.value - 1] = val
    return val


@primitive(68)
def compiledmethod_objectAt(rcvr, i, context, vm):
    return rcvr[i.value - 1]


@primitive(70)
def new(rcvr, context, vm):
    return vm.allocate(rcvr)


@primitive(71)
def new(rcvr, size, context, vm):
    return vm.allocate(rcvr, array_size=size.value)


@primitive(83)
def perform(rcvr, *args, context, vm):
    selector = args[-1]
    args = args[:-1]
    method = vm.lookup(rcvr.class_, selector)
    new_context = context.__class__(rcvr, method, vm)
    new_context.stack[:len(args)] = reversed(args)
    context.previous.next = new_context
    context._previous = None  # useful?
    vm.current_context = new_context


@primitive(110)
def identity(rcvr, arg, context, vm):
    return rcvr.address == arg.address


@primitive(111)
def objectClass(rcvr, context, vm):
    return rcvr.class_


@primitive(113)
def quitPrimitive(rcvr, context, vm):
    print_object(rcvr.slots[2])
    import ipdb; ipdb.set_trace()


@primitive(117)
def external_call(*args, context, vm):
    method = context.compiled_method
    pragma = method.literals[0]
    plugin = pragma[0].as_text()
    call = pragma[1].as_text()
    import importlib
    plugin_module = importlib.import_module(f'plugins.{plugin}')
    plugin_function = getattr(plugin_module, call)
    return plugin_function(*args, context, vm)


@primitive(240)
def utc_microsecond_clock(rcvr, context, vm):
    t = int(round(time.time() * 1000))
    return ImmediateInteger.create(t, vm.memory)


@primitive(254)
def VMParameter(rcvr, i, context, vm):
    # HARDCODED PARAMS FOR NOW
    params = {
        44: ImmediateInteger.create(1024, vm.memory)
    }
    return params[i.value]


@primitive(542)
def minusFloat(a, b, context, vm):
    return a.__class__.create(a.value - b.value, vm.memory)


@primitive(547)
def eqFloat(a, b, context, vm):
    return a.value == b.value


@primitive(550)
def divFloat(a, b, context, vm):
    return a.__class__.create(a.value / b.value, vm.memory)


def build_largepositiveint(value, vm):
    cls = vm.memory.largepositiveint
    size = (value.bit_length() + 7) // 8
    array_size = (size//(8 + 1)) + 1
    inst = vm.allocate(cls, array_size=array_size)
    byte_array = value.to_bytes(size, byteorder='little')
    inst.raw_slots = byte_array
    return inst


def print_object(receiver):
    print("receiver", receiver.display())
    print("object type", receiver.__class__.__name__, "kind", receiver.kind)
    print("class", receiver.class_.name)
    print("slots")
    if receiver.kind in range(9, 24):
        for i in range(len(receiver)):
            if i > 0 and i % 8 == 0:
                print()
            print("", hex(receiver[i]), end="")
        print()
        print(f'text "{receiver.as_text()}"')
        return
    for i in range(len(receiver.slots)):
        print(f"{i:2}   ", receiver[i].display())
    if hasattr(receiver, "instvars"):
        print("instvar in slots")
        for i in range(len(receiver.instvars)):
            print(f"{i:2}   ", receiver.instvars[i].display())
    if hasattr(receiver, "array"):
        print("array in slots")
        for i in range(len(receiver.array)):
            print(f"{i:2}   ", receiver.array[i].display())
