from ..spurobjects import ImmediateInteger as integer
from ..primitives import PrimitiveFail


def primitiveScreenDepth(rcvr, context, vm):
    from Xlib.display import Display
    root = Display().screen().root
    return integer.create(root.get_geometry().depth, vm.memory)


def primitiveUtcWithOffset(*args, context, vm):
    # import ipdb; ipdb.set_trace()
    raise PrimitiveFail
