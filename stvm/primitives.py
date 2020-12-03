import time
import struct
import importlib
from .spurobjects import ImmediateInteger as integer
from .spurobjects import ImmediateFloat

LargeNegativeIntClass = 32
LargePositiveIntClass = 33
SMALLINT_MAX = 1152921504606846975
SMALLINT_MIN = -1152921504606846976


nil = object()
primitives = {}


class PrimitiveFail(Exception):
    pass


unimpl = set()


def execute_primitive(number, context, vm, *args, **kwargs):
    memory = vm.memory
    try:
        receiver = args[0]
        fun = primitives[number]
        result = fun(receiver, *args[1:], context=context, vm=vm, **kwargs)
        result = receiver if result is None else result
        if fun.activate:
            vm.activate_context(result)
        else:
            result = python2st(result, memory)
            vm.activate_context(context.previous)
            vm.current_context.push(result)
        return result
    except KeyError:
        unimpl.add(number)
        # print("** Unimplemented", unimpl)
        raise PrimitiveFail
    except PrimitiveFail as e:
        raise e
    except Exception as e:
        if number in (117,):
            raise e
        raise PrimitiveFail


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
    if obj is nil:
        return memory.nil
    return obj


def primitive(numbers, activate=False):
    def inner_register(fun):
        fun.activate = activate
        if isinstance(numbers, range):
            for i in numbers:
                primitives[i] = fun
        else:
            primitives[numbers] = fun
        return fun
    return inner_register


@primitive(1)
def plus(a, b, context, vm):
    return smallint(a.value + b.value, vm)


@primitive(2)
def minus(a, b, context, vm):
    return smallint(a.value - b.value, vm)


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


@primitive(7)
def equalSmallint(a, b, context, vm):
    return a.value == b.value


@primitive(8)
def diff(a, b, context, vm):
    return a.value != b.value


@primitive(9)
def mult(a, b, context, vm):
    return smallint(a.value * b.value, vm)


@primitive(10)
def div(a, b, context, vm):
    if a.value % b.value != 0:
        raise PrimitiveFail('not divisible')
    return smallint(a.value // b.value)


@primitive(11)
def mod(a, b, context, vm):
    return smallint(a.value % b.value, vm)


@primitive(12)
def divRound(a, b, context, vm):
    return smallint(a.value // b.value, vm)


@primitive(13)
def quo(a, b, context, vm):
    return smallint(a.value // b.value, vm)


@primitive(14)
def bitand(a, b, context, vm):
    return smallint(a.value & b.value, vm)


@primitive(17)
def bitshift(self, shift, context, vm):
    if shift.value < 0:
        res = self.value >> (-shift.value)
    else:
        res = self.value << shift.value
    return smallint(res, vm)


# All these primitives should fail for a large negative number
@primitive(21)
def large_add(a, b, context, vm):
    a = to_int(a)
    b = to_int(b)
    res = a + b
    return large_or_small(res, vm)


@primitive(22)
def large_minus(a, b, context, vm):
    a = to_int(a)
    b = to_int(b)
    res = a - b
    return large_or_small(res, vm)


@primitive(23)
def large_less(a, b, context, vm):
    a = to_int(a)
    b = to_int(b)
    return a < b


@primitive(24)
def large_greater(a, b, context, vm):
    a = to_int(a)
    b = to_int(b)
    return a > b


@primitive(25)
def large_lessEq(a, b, context, vm):
    a = to_int(a)
    b = to_int(b)
    return a <= b


@primitive(26)
def large_greatEq(a, b, context, vm):
    a = to_int(a)
    b = to_int(b)
    return a >= b


@primitive(27)
def large_eq(a, b, context, vm):
    a = to_int(a)
    b = to_int(b)
    return a == b


@primitive(28)
def large_neq(a, b, context, vm):
    a = to_int(a)
    b = to_int(b)
    return a != b


@primitive(29)
def large_mult(a, b, context, vm):
    a = to_int(a)
    b = to_int(b)
    return large_or_small(a * b, vm)


@primitive(30)
def large_div(a, b, context, vm):
    a = to_int(a)
    b = to_int(b)
    if a % b != 0:
        raise PrimitiveFail('not divisible')
    return large_or_small(a // b, vm)


@primitive(31)
def large_mod(a, b, context, vm):
    a = to_int(a)
    b = to_int(b)
    res = a % b
    return large_or_small(res, vm)


@primitive(32)
def large_divRound(a, b, context, vm):
    a = to_int(a)
    b = to_int(b)
    res = a // b
    return large_or_small(res, vm)


primitive(33)(large_divRound)


@primitive(40)
def smallintAsFloat(self, context, vm):
    return ImmediateFloat.create(self, vm.memory)


@primitive(60)
def at(self, at, context, vm):
    return self[at.value - 1]


@primitive(61)
def at_put(self, at, val, context, vm):
    self[at.value - 1] = val
    return val


@primitive(62)
def basicSize(self, context, vm):
    return integer.create(len(self), vm.memory)


@primitive(68)
def compiledmethod_objectAt(rcvr, i, context, vm):
    return rcvr[i.value - 1]


@primitive(70)
def new(rcvr, context, vm):
    return vm.allocate(rcvr)


@primitive(71)
def new(rcvr, size, context, vm):
    return vm.allocate(rcvr, array_size=size.value)


@primitive(75)
def basicIdentityHash(self, context, vm):
    return integer.create(self.identity_hash, vm.memory)


@primitive(76)
def store_stackp(self, new_stackp, context, vm):
    nil = vm.memory.nil
    if self.stackp is nil:
        self.stackp = integer.create(0, vm.memory)
    if new_stackp > self.stackp:
        old = self.stackp
        self.stackp = new_stackp
        for i in range(old.value, new_stackp.value):
            self.stack[i] = nil
    else:
        self.stackp = new_stackp


@primitive(83, activate=True)
def perform(rcvr, selector, *args, context, vm):
    method = vm.lookup(rcvr.class_, selector)
    new_context = context.__class__(rcvr, method, vm.memory)
    new_context.stack[:len(args)] = args
    new_context.previous = context.previous
    return new_context


@primitive(85)
def signal(semaphore, context, vm):
    # vm.synchronous_signal(semaphore)
    ...


@primitive(86)
def wait(semaphore, context, vm):
    vm.wait(semaphore)


@primitive(87)
def resume(semaphore, context, vm):
    import ipdb; ipdb.set_trace()

    # vm.wait(semaphore)


@primitive(88)
def suspend(semaphore, context, vm):
    import ipdb; ipdb.set_trace()

    # vm.wait(semaphore)


@primitive(110)
def identity(rcvr, arg, context, vm):
    return rcvr.address == arg.address


@primitive(111)
def objectClass(rcvr, context, vm):
    return rcvr.class_


@primitive(113)
def quitPrimitive(rcvr, colargeintntext, vm):
    print_object(rcvr.slots[2])
    import ipdb; ipdb.set_trace()


@primitive(117)
def external_call(*args, context, vm):
    method = context.compiled_method
    pragma = method.literals[0]
    plugin = pragma[0].as_text()
    call = pragma[1].as_text()
    plugin_module = importlib.import_module(f'stvm.plugins.{plugin}')
    plugin_function = getattr(plugin_module, call)
    return plugin_function(*args, context, vm)


@primitive(125)
def signal_at_byte_left(self, threasold, context, vm):
    print("""Tell the interpreter the low-space threshold in bytes. When the free
	space falls below this threshold, the interpreter will signal the low-space
	semaphore, if one has been registered.""")


@primitive(129)
def special_object_oop(self, context, vm):
    return vm.memory.special_object_array


@primitive(148)
def clone(self, context, vm):
    cls = self.class_
    new = vm.allocate(cls, array_size=len(self))
    for i, v in enumerate(self.raw_slots):
        new.raw_slots[i] = v
    return new


@primitive(175)
def identity_hash(self, context, vm):
    return integer.create(self.identity_hash, vm.memory)


@primitive(range(201, 205), activate=True)
def closure_value(closure, *args, context, vm):
    outer_ctx = closure.outer_context
    method = outer_ctx.compiled_method
    rcvr = outer_ctx.receiver
    new_context = context.__class__(rcvr, method, vm.memory)
    new_context.pc = closure.startpc.value
    new_context.closure = closure
    new_context.stack = list(args)
    new_context.stack.extend(reversed(closure.copied))
    start_temps = method.num_args
    stop_temps = method.num_temps
    new_context.stack.extend(outer_ctx.stack[start_temps:stop_temps])

    new_context.previous = context.previous
    return new_context


@primitive(range(211, 223), activate=True)
def closure_value(closure, *args, context, vm):
    outer_ctx = closure.outer_context
    method = outer_ctx.compiled_method
    rcvr = outer_ctx.receiver
    new_context = context.__class__(rcvr, method, vm.memory)
    new_context.pc = closure.startpc.value
    new_context.closure = closure

    new_context.stack = list(args)
    new_context.stack.extend(reversed(closure.copied))
    start_temps = method.num_args
    stop_temps = method.num_temps
    new_context.stack.extend(outer_ctx.stack[start_temps:stop_temps])

    new_context.previous = context.previous
    return new_context


@primitive(211)
def context_at_put(ctx, at, val, context, vm):
    ctx.slots[at.value] = val
    return val


@primitive(240)
def utc_microsecond_clock(rcvr, context, vm):
    t = int(round(time.time() * 1000000))
    return integer.create(t, vm.memory)

@primitive(242)
def signal_at_microseconds(self, sema, microsecs, context, vm):
    memory = vm.memory
    index = memory.special_array["timer_semaphore"]
    # import ipdb; ipdb.set_trace()

    if sema is memory.nil:
        memory.special_object_oop[index] = nil
        vm.nextWakeupUsecs = 0
        return
    memory.special_object_array[index] = sema
    memory.timer_semaphore = sema
    vm.nextWakeupUsecs = microsecs.value


@primitive(254)
def VMParameter(rcvr, at, *put, context=None, vm=None):
    if put:
        vm.params[at.value] = put[0]
        return at.__class__.create(0, vm.memory)
    return vm.params[at.value]


@primitive(542)
def minusFloat(a, b, context, vm):
    return a.__class__.create(a.value - b.value, vm.memory)


@primitive(543)
def lessFloat(a, b, context, vm):
    return a.value < b.value


@primitive(544)
def greaterFloat(a, b, context, vm):
    return a.value > b.value


@primitive(545)
def lessEqFloat(a, b, context, vm):
    return a.value <= b.value


@primitive(547)
def eqFloat(a, b, context, vm):
    try:
        return a.value == b.value
    except Exception:
        a = a.as_float()
        b = b.as_float()
        return a == b


@primitive(549)
def multFloat(a, b, context, vm):
    return a.__class__.create(a.value * b.value, vm.memory)


@primitive(550)
def divFloat(a, b, context, vm):
    return a.__class__.create(a.value / b.value, vm.memory)


@primitive(551)
def truncatedFloat(a, context, vm):
    return integer.create(int(a.value), vm.memory)


@primitive(552)
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


def smallint(r, vm):
    try:
        return integer.create(r, vm.memory)
    except struct.error:
        raise PrimitiveFail("out of range")


def large_or_small(r, vm):
    if SMALLINT_MIN <= r <= SMALLINT_MAX:
        return integer.create(r, vm.memory)
    length = ceil((len(hex(r)) - 2) / 2)
    rb = int.to_bytes(r, byteorder="little", length=length)
    if r < 0:
        result = vm.allocate(vm.memory.largenegativeint, array_size=length)
    else:
        result = vm.allocate(vm.memory.largepositiveint, array_size=length)
    result.raw_slots = rb
    return result


def to_int(e):
    val = int(e)
    if e.kind == -1:
        return val
    if e.class_index == LargePositiveIntClass:
        return val
    if e.class_index == LargeNegativeIntClass:
        return -val
    raise Exception("Unknown problem")
