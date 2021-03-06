from .vm import Quit, Continuate, Context, BlockClosure, BlockContinuate
from .image_reader32 import build_int, build_char


primitives = {}


class PrimitiveFail(Exception):
    pass


def execute_primitive(primitive_number, context):
    primitive = primitives[primitive_number]
    return primitive(context)


def register_primitive(o):
    def func(c):
        type_list = o if isinstance(o, tuple) else (o,)
        for t in type_list:
            primitives[t] = c
        return c
    return func


def build_ascii_string(s, vm):  # Refactor me... signature is bad
    s = s.encode('ascii', 'ignore')
    inst = vm.memory_allocator.allocate(vm.mem.bytestring, size=len(s))
    inst_obj = inst.obj
    for i, c in enumerate(s):
        inst_obj[i] = c
    return inst


def build_largepositiveint(value, vm):  # Refactor me... signature is bad
    cls = vm.mem.largepositiveint
    size = (value.bit_length() + 7) // 8
    inst = vm.memory_allocator.allocate(cls, size=size)
    byte_array = value.to_bytes(size, byteorder='little')
    inst_obj = inst.obj
    for i, byte in enumerate(byte_array):
        inst_obj[i] = byte
    return inst


@register_primitive(1)
def plus(context):
    # receiver = context.receiver
    # arg = context.temporaries[0]
    # res = build_int(receiver.obj.value + arg.obj.value, context.vm.mem)
    # print(f"   {receiver.obj.value} + {arg.obj.value} == {res.value}")
    # return res

    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    res = left + right
    print(f"   {left} + {right} == {left + right}")
    if res > 2147483648:
        return build_largepositiveint(res, context.vm)
    if res < -2147483648:
        import ipdb; ipdb.set_trace()
    return build_int(res, context.vm.mem)


@register_primitive(2)
def minus(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    res = build_int(receiver.obj.value - arg.obj.value, context.vm.mem)
    print(f"   {receiver.obj.value} - {arg.obj.value} == {res.value}")
    return res


@register_primitive(3)
def less(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    print(f"   {left} < {right} == {left < right}")
    if left < right:
        return context.vm.mem.true
    return context.vm.mem.false


@register_primitive(4)
def greater(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    print(f"   {left} > {right} == {left > right}")
    if left > right:
        return context.vm.mem.true
    return context.vm.mem.false


@register_primitive(5)
def lessOrEqual(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    print(f"   {left} <= {right} == {left <= right}")
    if left <= right:
        return context.vm.mem.true
    return context.vm.mem.false


@register_primitive(6)
def lessOrEqual(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    print(f"   {left} >= {right} == {left >= right}")
    if left >= right:
        return context.vm.mem.true
    return context.vm.mem.false


@register_primitive(7)
def equal(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    if receiver.obj == arg.obj:
        return context.vm.mem.true
    return context.vm.mem.false


@register_primitive(9)
def mult(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    res = left + right
    print(f"   {left} * {right} == {res}")
    if res > 2147483648:
        res = build_largepositiveint(res, context.vm)
    else:
        res = build_int(res, context.vm.mem)
    return res


@register_primitive(10)
def divide(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    res = receiver.obj.value / arg.obj.value
    print(f"   {receiver.obj.value} / {arg.obj.value} == {res}")
    if res % 10 == 0:
        return build_int(int(res), context.vm.mem)
    raise PrimitiveFail()


@register_primitive(11)
def mod(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    res = build_int(receiver.obj.value % arg.obj.value, context.vm.mem)
    print(f"   {receiver.obj.value} % {arg.obj.value} == {res.value}")
    return res



@register_primitive(12)
def div(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    res = build_int(receiver.obj.value // arg.obj.value, context.vm.mem)
    print(f"   {receiver.obj.value} // {arg.obj.value} == {res.value}")
    return res


@register_primitive(13)
def quo(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    res = build_int(int(float(left) / right), context.vm.mem)
    print(f"   {left} quo: {right} == {res.as_int()}")
    return res


@register_primitive(14)
def bitand(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    res = left & right
    print(f"   {left} & {right} == {res}")
    if res > 2147483648:
        res = build_largepositiveint(res, context.vm)
    else:
        res = build_int(res, context.vm.mem)
    return res


@register_primitive(17)
def bitshift(context):
    left = context.receiver.obj.as_int()
    shift = context.temporaries[0].obj.as_int()
    if shift < 0:
        res = left >> (-shift)
    else:
        res = left << shift
    print(f"   {left} shift: {shift} == {res}")
    if res > 2147483648:
        res = build_largepositiveint(res, context.vm)
    else:
        res = build_int(res, context.vm.mem)
    return res


@register_primitive(21)
def largeint_plus(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    res = build_largepositiveint(left + right, context.vm)
    print(f"   {left} + {right} == {left + right}")
    return res


@register_primitive(22)
def largeint_plus(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    res = left - right
    print(f"   {left} - {right} == {left + right}")
    if res <= 2147483648:
        res  = build_int(res, context.vm.mem)
    else:
        res = build_largepositiveint(res, context.vm)
    return res


@register_primitive(23)
def largeint_inf(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    print(f"   {left} < {right} == {left == right}")
    if left == right:
        return context.vm.mem.true
    return context.vm.mem.false


@register_primitive(25)
def largeint_infeq(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    print(f"   {left} <= {right} == {left <= right}")
    if left <= right:
        return context.vm.mem.true
    return context.vm.mem.false


@register_primitive(29)
def largeint_mult(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    res = build_largepositiveint(left * right, context.vm)
    print(f"   {left} * {right} == {left * right}")
    return res


@register_primitive(31)
def largeint_divide(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    res = build_largepositiveint(int(left / right), context.vm)
    print(f"   {left} / {right} == {left / right}")
    return res


@register_primitive(32)
def largeint_div(context):
    left = context.receiver.obj.as_int()
    right = context.temporaries[0].obj.as_int()
    res = build_largepositiveint(left // right, context.vm)
    print(f"   {left} // {right} == {left // right}")
    return res


@register_primitive(60)
def at(context):
    receiver = context.receiver
    index = context.temporaries[0].obj.value
    res = receiver.obj.array[index - 1]
    if isinstance(res, memoryview):
        res = build_int(int.from_bytes(res.tobytes(), byteorder='little'), context.vm.mem)
    return res


@register_primitive(61)
def at_put(context):
    receiver = context.receiver
    at = context.temporaries[0].obj.value
    value = context.temporaries[1]
    receiver.obj.array[at - 1] = value.obj
    return value


@register_primitive(62)
def size(context):
    receiver = context.receiver

    return build_int(len(receiver.array), context.vm.mem)


@register_primitive(63)
def string_at(context):
    arg = context.temporaries[0].obj.value
    string = context.receiver.obj
    return build_char(string[arg - 1][0], context.vm.mem)


@register_primitive(64)
def string_at_put(context):
    at = context.temporaries[0].obj.value
    value = context.temporaries[1]
    string = context.receiver.obj
    string[at - 1] = ord(value.obj.value)
    return value


@register_primitive((65, 66, 67))
def writestream_next_put(context):
    raise PrimitiveFail()
    # value = context.temporaries[0]
    # stream = context.receiver.obj
    # current_index = stream[1].value
    #
    # if stream.class_ is context.vm.mem.array:
    #     stream[0][current_index] = value.obj
    # else:
    #     stream[0][current_index] = ord(value.obj.value)
    # stream.instvars[1] = build_int(current_index + 1, context.vm.mem)
    # return value


@register_primitive(70)
def new(context):
    cls = context.receiver
    inst = context.vm.memory_allocator.allocate(cls)
    return inst


@register_primitive(71)
def newWithArg(context):
    arg = context.temporaries[0]
    cls = context.receiver
    inst = context.vm.memory_allocator.allocate(cls, size=arg)
    return inst


@register_primitive(75)
def hash_(context):
    receiver = context.receiver
    return build_int(receiver.address | 0x1, context.vm.mem)


@register_primitive(83)
def perform(context):
    selector = context.temporaries[0].obj
    receiver = context.receiver
    compiled_method = receiver.class_.lookup(selector)
    context.compiled_method = compiled_method
    context.receiver = receiver
    del context.temporaries[0]


@register_primitive(84)
def perform_with_args(context):
    import ipdb; ipdb.set_trace()

    return None


@register_primitive(85)
def signal(context):
    cls = context.receiver
    # inst = context.vm.memory_allocator.allocate(cls)
    import ipdb; ipdb.set_trace()

    return cls


@register_primitive(86)
def wait(context):
    cls = context.receiver
    # inst = context.vm.memory_allocator.allocate(cls)
    import ipdb; ipdb.set_trace()

    return cls


@register_primitive(105)
def string_replace(context):
    string = context.receiver.obj
    start = context.temporaries[0].obj.value
    stop = context.temporaries[1].obj.value
    with_ = context.temporaries[2].obj
    starting_at = context.temporaries[3].obj.value
    rep_offset = starting_at - start
    cls = string.class_
    array_cls = context.vm.mem.array
    for i in range(start - 1, stop):
        if cls == array_cls:
            string[i] = with_[i + rep_offset]
        else:
            string[i] = int.from_bytes(with_[i + rep_offset].tobytes(), 'little')
    return context.receiver


@register_primitive(110)
def identical(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    print(f"   {receiver.address} == {arg.address} ? {receiver.address == arg.address}")
    if receiver.address == arg.address:
        return context.vm.mem.true
    return context.vm.mem.false


@register_primitive(111)
def primitive_class(context):
    receiver = context.receiver
    return receiver.class_


@register_primitive(113)
def quit(context):
    raise Quit()


@register_primitive(117)
def external_call(context):
    method = context.compiled_method
    pragma = method.literals[0]
    plugin = pragma[0].as_text()
    call = pragma[1].as_text()
    nb_args = method.obj.method_header.num_args
    import importlib
    plugin_module = importlib.import_module(f'stvm.plugins.{plugin}')
    plugin_function = getattr(plugin_module, call)
    args = context.temporaries[:nb_args]
    result = plugin_function(context, *args)
    if result is None:
        return context.vm.mem.nil
    return result


@register_primitive(121)
def image_name(context):
    # from os import path
    # name = path.basename(path.splitext(context.vm.image_file)[0])
    # return build_ascii_string(name, context.vm)
    return build_ascii_string(context.vm.image_file, context.vm)


@register_primitive(135)
def millisecond_clock(context):
    import time
    millis = int(round(time.time() * 1000))
    milis_mask = 0x1FFFFFFF
    res = build_int(millis & milis_mask, context.vm.mem)
    return res


@register_primitive(148)
def clone(context):
    receiver = context.receiver
    cls = receiver.class_
    inst = context.vm.memory_allocator.allocate(cls, size=len(receiver.array))
    origin_address = receiver.obj.address
    new_address = inst.obj.address
    memory = context.vm.mem.raw
    memory[new_address + 8 : inst.obj.end_address] = memory[origin_address + 8: receiver.obj.end_address]
    context.vm.mem.__getitem__.cache_clear()
    inst = context.vm.mem[new_address]
    return inst


@register_primitive(170)
def as_character(context):
    value = context.temporaries[0].obj.value  # the int value of the char
    return build_char(value, context.vm.mem)


@register_primitive(175)
def behavior_hash(context):
    receiver = context.receiver.obj
    return build_int(receiver.header.identity_hash, context.vm.mem)


@register_primitive(198)
def quit(context):
    raise PrimitiveFail()


@register_primitive((201, 202, 203, 204, 221))
def closureValueNoContextSwitch(context):
    closure_obj = context.receiver.obj
    outer_context = closure_obj.home_context

    closure = BlockClosure(raw_bytecode=closure_obj.bytecode,
                           compiled_method=closure_obj,
                           literals=closure_obj.literals)

    temp_len = len(context.temporaries)
    new_temps = [context.vm.mem.nil] * temp_len
    if closure_obj.copied:
        new_temps[0:temp_len] = closure_obj.copied
    new_temps[0:0] = context.args

    context.compiled_method = closure
    context.outer_context = outer_context
    context.receiver = outer_context.receiver
    context.temporaries = new_temps


@register_primitive(235)
def nop(context):
    raise PrimitiveFail()


@register_primitive(240)
def utc_microsecond_clock(context):
    import time
    t = int(round(time.time() * 1000))
    res = build_largepositiveint(t, context.vm)
    print(f'    -> UTC {t}')
    return res


@register_primitive((171, 199, 256, 257, 258, 260, 262, 264, 265, 267, 269))
def nop(context):
    raise PrimitiveFail()
