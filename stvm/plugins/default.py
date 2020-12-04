from ..spurobjects import ImmediateInteger as integer


def primitiveScreenDepth(rcvr, context, vm):
    from Xlib.display import Display
    root = Display().screen().root
    return integer.create(root.get_geometry().depth, vm.memory)
