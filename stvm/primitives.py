from .vm import Quit, Continuate, Context, BlockClosure
from .image_reader32 import ImmediateInteger


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


def build_int(value, memory):
    immediate = ImmediateInteger(memory=memory)
    immediate.value = value
    value <<= 1
    value &= 0xFFFFFFFE
    immediate.address = value
    return immediate


@register_primitive(1)
def plus(context):
    receiver = context.receiver
    arg = context.temporaries[0]
    res = build_int(receiver.obj.value + arg.obj.value, context.vm.mem)
    print("    == ", res.value)
    return res


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


@register_primitive(60)
def at(context):
    receiver = context.receiver
    index = context.temporaries[0].obj.value
    return receiver.obj.array[index]


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
    if receiver.address == arg.address:
        return context.vm.mem.true
    return context.vm.mem.false


@register_primitive(113)
def quit(context):
    raise Quit()


@register_primitive(148)
def clone(context):
    receiver = context.receiver
    cls = receiver.class_
    inst = context.vm.memory_allocator.allocate(cls)
    idhash = inst.obj.header.identity_hash
    origin_address = receiver.obj.address
    new_address = inst.obj.address
    memory = context.vm.mem.raw
    memory[new_address : inst.obj.end_address] = memory[origin_address : receiver.obj.end_address]
    context.vm.mem.__getitem__.cache_clear()
    inst = context.vm.mem[new_address]
    return inst




@register_primitive(198)
def quit(context):
    raise PrimitiveFail()


@register_primitive((201, 221))
def closureValueNoContextSwitch(context):
    closure_obj = context.receiver.obj
    closure = BlockClosure(raw_bytecode=closure_obj.bytecode,
                           compiled_method=closure_obj,
                           outer_context=context)
    outer_context = closure.obj.home_context

    closure = BlockClosure(raw_bytecode=closure_obj.bytecode,
                           compiled_method=closure_obj,
                           literals=closure_obj.literals,
                           outer_context=outer_context)
    new_context = Context(
        compiled_method=closure,
        receiver=outer_context.receiver,
        previous_context=context,
        temps=outer_context.temporaries,
    )
    print('Start closure execution')
    raise Continuate()


@register_primitive((202))
def closureValueNoContextSwitch(context):
    arg = context.temporaries[0]
    closure_obj = context.receiver.obj
    closure = BlockClosure(raw_bytecode=closure_obj.bytecode,
                           compiled_method=closure_obj,
                           outer_context=context)
    outer_context = closure.obj.home_context

    closure = BlockClosure(raw_bytecode=closure_obj.bytecode,
                           compiled_method=closure_obj,
                           literals=closure_obj.literals,
                           outer_context=outer_context)
    new_context = Context(
        compiled_method=closure,
        receiver=outer_context.receiver,
        previous_context=context,
        temps=outer_context.temporaries,
        args=[arg],
    )
    print('Start closure execution')
    raise Continuate()



@register_primitive(256)
def nop(context):
    return context.receiver
