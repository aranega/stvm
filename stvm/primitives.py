import time
from datetime import datetime as dt
import math
import struct
import importlib
from .utils import *
from .spurobjects import ImmediateInteger as integer
from .spurobjects import ImmediateFloat as smallfloat
from .spurobjects import ImmediateChar as char


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
        print("** Unimplemented", sorted(unimpl))
        if number in (19, 38, 65, 66, 77, 90, 91, 93, 94, 107, 108, 149, 159, 177, 195, 197, 198, 199):
            raise PrimitiveFail
        raise Exception(f"Missing primitive {number} called with [{', '.join(a.display() for a in args)}]")
    except PrimitiveFail as e:
        raise e
    except Exception as e:
        if number in (60, 105, *range(1, 16), *range(541, 560)):
            raise PrimitiveFail
        raise e
        raise PrimitiveFail


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
    return smallint(a.value // b.value, vm)


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


@primitive(15)
def bitor(a, b, context, vm):
    return smallint(a.value | b.value, vm)


@primitive(16)
def bitxor(a, b, context, vm):
    return smallint(a.value ^ b.value, vm)


@primitive(17)
def bitshift(self, shift, context, vm):
    if shift.value < 0:
        res = self.value >> (-shift.value)
    else:
        res = self.value << shift.value
    return smallint(res, vm)


@primitive(18)
def make_point(x, y, context, vm):
    point_class = vm.memory.point
    point = vm.allocate(point_class)
    point[0] = x
    point[1] = y
    return point


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


@primitive(38)
def float_at(f, index, context, vm):
    return f[index.value - 1]


@primitive(40)
def smallintAsFloat(self, context, vm):
    return smallfloat.create(self, vm.memory)


@primitive(60)
def at(self, at, context, vm):
    # if self.class_.name == "Weak"
    return self.basic_at(at.value - 1)


@primitive(61)
def at_put(self, at, val, context, vm):
    self.basic_at_put(at.value - 1, val)
    return val


@primitive(62)
def basicSize(self, context, vm):
    return integer.create(len(self), vm.memory)


@primitive(63)
def string_at(self, i, context, vm):
    return char.create(chr(self.raw_at(i.value - 1)), vm.memory)


@primitive(64)
def string_at_put(self, i, val, context, vm):
    self[i.value - 1] = val
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


@primitive(75)
def basicIdentityHash(self, context, vm):
    if self.identity_hash == 0:
        h = new_object_hash(vm) & 0x3FFFFF
        self.h2 = (self.h2 & 0xFFC00000) | h
        self.header2[:] = struct.pack("I", self.h2)
        self.identity_hash = h
    return integer.create(self.identity_hash, vm.memory)


def new_object_hash(vm):
    last = vm.last_hash
    while "hash is zero":
        last *= 16807
        h = last + (last >> 4)
        if h & 0x3FFFFF != 0:
            break
    vm.last_hash = last
    return h

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
    vm.synchronous_signal(semaphore)


@primitive(86)
def wait(semaphore, context, vm):
    vm.wait(semaphore)


@primitive(87)
def resume(process, context, vm):
    vm.resume(process)


@primitive(88)
def suspend(process, context, vm):
    if process is not vm.active_process:
        raise PrimitiveFail("not the active process")
    context.push(vm.memory.nil)
    vm.suspend_active()


@primitive(101)
def be_cursor(self, mask_form, context, vm):
    # mask    cursor_effect
    # 0		  0		transparent (underlying pixel shows through)
	# 1		  1		opaque black
	# 1		  0		opaque white
	# 0		  1		invert the underlying pixel"
    shape = self[0]
    mask = mask_form[0]
    width = self[1].value
    height = self[2].value
    for rshape, rmask in zip(shape, mask):
        line = ""
        z = zip(f"{rshape.value:032b}", f"{rmask.value:032b}")
        for j, (b, m) in enumerate(z):
            if b == "0" and m == "0":
                line += " "
            elif b == "1" and m == "1":
                line += "#"
            elif b == "1" and m == "0":
                line += "O"
            else:
                line += "i"
            if j > 0 and j % width == 0:
                break
        print(line)


@primitive(102)
def be_display(self, context, vm):
    # record object in special object array
    vm.memory.special_object_array[14] = self


@primitive(105)
def replacefrom_to_with_startingat(self, start, stop, other, start_other, context, vm):
    start = start.value - 1
    stop = stop.value
    start_other = start_other.value - 1
    for k, i in enumerate(range(start, stop), start=start_other):
        self[i] = other[k]
    return self


@primitive(106)
def screen_size(rcvr, context, vm):
    from Xlib.display import Display
    display = Display()
    geometry = display.screen().root.get_geometry()
    width = geometry.width
    height = geometry.height
    point = vm.allocate(vm.memory.point)
    point.slots[0] = integer.create(width, vm.memory)
    point.slots[1] = integer.create(height, vm.memory)
    return point


@primitive(110)
def identity(rcvr, arg, context, vm):
    return rcvr.address == arg.address


@primitive(111)
def objectClass(rcvr, *arg, context, vm):
    if arg:
        return arg[0].class_
    return rcvr.class_


@primitive(113)
def quitPrimitive(rcvr, colargeintntext, vm):
    print_object(rcvr.slots[2])
    import ipdb; ipdb.set_trace()


@primitive(117)
def external_call(*args, context, vm):
    method = context.compiled_method
    pragma = method.literals[0]
    try:
        module = pragma[0].as_text()
    except Exception:
        module = "default"
    call = pragma[1].as_text()
    plugin_module = importlib.import_module(f'stvm.plugins.{module}')
    plugin_function = getattr(plugin_module, call)
    return plugin_function(*args, context=context, vm=vm)


@primitive(121)
def image_name(self, context, vm):
    return to_bytestring(str(vm.image.file), vm)


@primitive(125)
def signal_at_byte_left(self, threasold, context, vm):
    print("""Tell the interpreter the low-space threshold in bytes. When the free
	space falls below this threshold, the interpreter will signal the low-space
	semaphore, if one has been registered.""")


@primitive(129)
def special_object_oop(self, context, vm):
    return vm.memory.special_object_array


# this primitive is obsolete
@primitive(133)
def set_keycode(sensor, keycode, context, vm):
    vm.interrupt_keycode = keycode.value


@primitive(135)
def millisecond_clock(self, context, vm):
    ms = int(round(dt.now().timestamp() + 2177452800))
    return integer.create(ms & 0x1FFFFFFF, vm.memory)


@primitive(142)
def vm_paths(self, context, vm):
    import os
    return to_bytestring(os.getcwd() + "/", vm)


@primitive(148)
def clone(self, context, vm):
    cls = self.class_
    new = vm.allocate(cls, array_size=len(self))
    for i, v in enumerate(self.raw_slots):
        new.raw_slots[i] = v
    return new


@primitive(149)
def get_system_attribute(self, index, context, vm):
    index = index.value - 2
    if index < 0:
        # not handled at the moment
        return nil
    import sys
    argv = sys.argv
    if index >= len(argv):
        return nil
    return to_bytestring(argv[index], vm)


@primitive(169)
def not_identical(a, b, context, vm):
    return a.address != b.address


@primitive(170)
def immediate_aschar(cls, value, context, vm):
    return char.create(chr(value.value), vm.memory)


@primitive(171)
def immediate_asint(self, context, vm):
    return self.as_immediate_int()


@primitive(175)
def identity_hash(self, context, vm):
    return integer.create(self.identity_hash, vm.memory)


@primitive(176)
def max_identity_hash(self, context, vm):
    return integer.create(0x3FFFFF, vm.memory)


@primitive(188)
def execute_method_argsarray(receiver, args_array, method, context, vm):
    import ipdb; ipdb.set_trace()


@primitive(189)
def execute_method(receiver, args, method, context, vm):
    import ipdb; ipdb.set_trace()


@primitive(195)
def next_unwind_context_upto(self, upto, context, vm):
    tmp = self
    while tmp.sender and tmp.sender is not upto:
        if tmp.is_unwind():
            return tmp
        tmp = tmp.sender
    return nil


@primitive(197)
def find_handler_context(self, context, vm):
    tmp = self
    while tmp:
        if tmp.is_handler_or_signaling():
            return tmp
        tmp = tmp.sender
    return nil


@primitive(range(201, 205), activate=True)
def closure_value(closure, *args, context, vm):
    outer_ctx = closure.outer_context
    method = outer_ctx.compiled_method
    rcvr = outer_ctx.receiver
    new_context = context.__class__(rcvr, method, vm.memory)
    new_context.pc = closure.startpc.value
    new_context.closure = closure
    new_context.stack = [*args]
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

    new_context.stack = [*args]
    new_context.stack.extend(reversed(closure.copied))
    start_temps = method.num_args
    stop_temps = method.num_temps
    new_context.stack.extend(outer_ctx.stack[start_temps:stop_temps])

    new_context.previous = context.previous
    return new_context


@primitive(210)
def context_at(ctx, at, context, vm):
    return ctx.stack[at.value]


@primitive(211)
def context_at_put(ctx, at, val, context, vm):
    ctx.stack[at.value - 1] = val
    return val


@primitive(240)
def utc_microsecond_clock(rcvr, context, vm):
    t = int(round((dt.utcnow().timestamp() + 2177452800) * 1000000))
    return integer.create(t, vm.memory)


@primitive(241)
def local_microsecond_clock(rcvr, context, vm):
    t = int(round((dt.now().timestamp() + 2177452800) * 1000000))
    return integer.create(t, vm.memory)


@primitive(242)
def signal_at_microseconds(self, sema, microsecs, context, vm):
    memory = vm.memory
    index = memory.special_array["timer_semaphore"]

    if sema is memory.nil:
        memory.special_object_oop[index] = nil
        vm.nextWakeupUsecs = 0
        return
    memory.special_object_array[index] = sema
    memory.timer_semaphore = sema
    vm.nextWakeupUsecs = microsecs.value


primitive(136)(signal_at_microseconds)


@primitive(254)
def VMParameter(rcvr, at, *put, context=None, vm=None):
    if put:
        vm.params[at.value] = put[0]
        return at.create(0, vm.memory)
    return vm.params[at.value]


@primitive(541)
def addFloat(a, b, context, vm):
    return float_or_boxed(a.as_float() + b.as_float(), vm)

primitive(41)(addFloat)


@primitive(542)
def minusFloat(a, b, context, vm):
    return float_or_boxed(a.as_float() - b.as_float(), vm)

primitive(42)(minusFloat)


@primitive(543)
def lessFloat(a, b, context, vm):
    return a.as_float() < b.as_float()

primitive(43)(lessFloat)


@primitive(544)
def greaterFloat(a, b, context, vm):
    return a.as_float() > b.as_float()

primitive(44)(greaterFloat)


@primitive(545)
def lessEqFloat(a, b, context, vm):
    return a.as_float() <= b.as_float()

primitive(45)(lessEqFloat)


@primitive(546)
def greaterEqFloat(a, b, context, vm):
    return a.as_float() >= b.as_float()

primitive(46)(greaterEqFloat)

@primitive(547)
def eqFloat(a, b, context, vm):
    return a.as_float() == b.as_float()

primitive(47)(eqFloat)


@primitive(548)
def neqFloat(a, b, context, vm):
    return a.as_float() != b.as_float()

primitive(48)(neqFloat)


@primitive(549)
def multFloat(a, b, context, vm):
    return float_or_boxed(a.as_float() * b.as_float(), vm)

primitive(49)(multFloat)


@primitive(550)
def divFloat(a, b, context, vm):
    return float_or_boxed(a.as_float() / b.as_float(), vm)

primitive(50)(divFloat)


@primitive(551)
def truncatedFloat(a, context, vm):
    return integer.create(int(a.as_float()), vm.memory)

primitive(51)(truncatedFloat)


@primitive(552)
def factionalPart(a, context, vm):
    return float_or_boxed(a.as_float() % 1, vm)

primitive(52)(factionalPart)


@primitive(553)
def exponent(a, context, vm):
    addr = a.address
    exp = (addr >> 56) + 896 - 0x3FE - 1
    return integer.create(exp, vm.memory)


@primitive(53)
def exponent_boxed(a, context, vm):
    value = struct.unpack(">Q", struct.pack(">d", a.as_float()))[0]
    exp = (value >> 52) & 0x7FF
    return integer.create(exp, vm.memory)


@primitive(554)
def power2(a, b, context, vm):
    return float_or_boxed(a.as_float() * 2 ** b.as_float(), vm)

primitive(54)(power2)


@primitive(555)
def sqrt(a, context, vm):
    return float_or_boxed(math.sqrt(a.as_float()), vm)

primitive(55)(sqrt)


@primitive(556)
def sine(a, context, vm):
    return float_or_boxed(math.sin(a.as_float()), vm)

primitive(56)(sine)


@primitive(557)
def arctan(a, context, vm):
    return float_or_boxed(math.atan(a.as_float()), vm)

primitive(57)(arctan)


@primitive(558)
def log10(a, context, vm):
    return float_or_boxed(math.log(a.as_float(), 10), vm)

primitive(58)(log10)


@primitive(559)
def exp(a, context, vm):
    return float_or_boxed(math.exp(a.as_float()), vm)

primitive(59)(exp)


def smallint(r, vm):
    try:
        return integer.create(r, vm.memory)
    except struct.error:
        raise PrimitiveFail("out of range")


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
