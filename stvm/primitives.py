from .vm import Quit
from .image_reader32 import ImmediateInteger


primitives = {}


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


@register_primitive(70)
def new(context):
    cls = context.receiver
    inst = context.vm.memory_allocator.allocate(cls)
    return inst


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


@register_primitive(256)
def nop(*args):
    pass
