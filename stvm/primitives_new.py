primitives = {}


class PrimitiveFail(Exception):
    pass


def execute_primitive(number, context, vm, *args, **kwargs):
    memory = vm.memory
    # args = [st2python(obj, memory) for obj in args
    try:
        result = primitives[number](args[0], *args[1:], context, vm, **kwargs)
        return python2st(result, memory)
    except Exception:
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


@primitive(110)
def identity(rcvr, arg, context, vm):
    return rcvr.address == arg.address
