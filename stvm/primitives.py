from .vm import Quit, Continuate, Context, BlockClosure
from .image_reader32 import build_int


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


@register_primitive(1)
def plus(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    res = build_int(receiver.obj.value + arg.obj.value, context.vm.mem)
    print(f"   {receiver.obj.value} + {arg.obj.value} == {res.value}")
    return res


@register_primitive(2)
def plus(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    res = build_int(receiver.obj.value - arg.obj.value, context.vm.mem)
    print(f"   {receiver.obj.value} - {arg.obj.value} == {res.value}")
    return res


@register_primitive(3)
def less(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    print(f"   {receiver.obj.value} < {arg.obj.value} == { receiver.obj < arg.obj}")
    if receiver.obj < arg.obj:
        return context.vm.mem.true
    return context.vm.mem.false


@register_primitive(4)
def greater(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    print(f"   {receiver.obj.value} > {arg.obj.value} == { receiver.obj > arg.obj}")
    if receiver.obj > arg.obj:
        return context.vm.mem.true
    return context.vm.mem.false


@register_primitive(5)
def lessOrEqual(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    if receiver.obj <= arg.obj:
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
def plus(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    res = build_int(receiver.obj.value * arg.obj.value, context.vm.mem)
    print(f"   {receiver.obj.value} * {arg.obj.value} == {res.value}")
    return res


@register_primitive(12)
def plus(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    res = build_int(receiver.obj.value // arg.obj.value, context.vm.mem)
    print(f"   {receiver.obj.value} // {arg.obj.value} == {res.value}")
    return res


@register_primitive(60)
def at(context):
    receiver = context.receiver
    index = context.temporaries[0].obj.value
    return receiver.obj.array[index - 1]


@register_primitive(62)
def size(context):
    receiver = context.receiver
    return build_int(len(receiver.array), context.vm.mem)


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


@register_primitive(85)
def signal(context):
    cls = context.receiver
    # inst = context.vm.memory_allocator.allocate(cls)
    return cls


@register_primitive(86)
def wait(context):
    cls = context.receiver
    # inst = context.vm.memory_allocator.allocate(cls)
    return cls


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


@register_primitive(121)
def image_name(context):
    from os import path
    return path.basename(path.splitext(context.vm.image_file)[0])


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




@register_primitive(198)
def quit(context):
    raise PrimitiveFail()


@register_primitive((201, 221))
def closureValueNoContextSwitch(context):
    closure_obj = context.receiver.obj
    outer_context = closure_obj.home_context

    closure = BlockClosure(raw_bytecode=closure_obj.bytecode,
                           compiled_method=closure_obj,
                           literals=closure_obj.literals,
                           outer_context=outer_context)
    new_context = Context(
        compiled_method=closure,
        receiver=outer_context.receiver,
        previous_context=context,
        temps=closure_obj.copied + outer_context.temporaries,
    )
    print('Start closure execution')
    raise Continuate()


@register_primitive((202))
def closureValueNoContextSwitch(context):
    closure_obj = context.receiver.obj
    outer_context = closure_obj.home_context

    closure = BlockClosure(raw_bytecode=closure_obj.bytecode,
                           compiled_method=closure_obj,
                           literals=closure_obj.literals,
                           outer_context=outer_context)

    new_context = Context(
        compiled_method=closure,
        receiver=outer_context.receiver,
        previous_context=context,
        temps=closure_obj.copied + outer_context.temporaries,
        args=context.args,
    )
    print('Will start closure execution')
    import ipdb; ipdb.set_trace()

    raise Continuate()


@register_primitive(240)
def utc_microsecond_clock(context):
    import time
    return build_int(int(round(time.time() * 1000)), context.vm.mem)



@register_primitive(256)
def nop(context):
    raise PrimitiveFail()


@register_primitive(257)
def nop(context):
    raise PrimitiveFail()


@register_primitive(260)
def nop(context):
    raise PrimitiveFail()


@register_primitive(264)
def nop(context):
    raise PrimitiveFail()
