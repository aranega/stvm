from .objects import VariableSizedW, SpurObject

CONTEXT_CLASS = 36
CLOSURE_CLASS = 37


def spurobject(t, class_index):
    def func(c):
        SpurObject.special_subclasses[(t, class_index)] = c
        return c
    return func


# class Slot(object):
#     def __init__(self, index):
#         self.index = index
#
#     def __get__(self, obj, objtype=None):
#         return obj[self.index]


@spurobject(3, class_index=CONTEXT_CLASS)
class Context(VariableSizedW):
    @property
    def sender(self):
        return self[0]

    @property
    def pc(self):
        return self[1]

    @property
    def stackp(self):
        return self[2]

    @property
    def compiled_method(self):
        return self[3]

    @property
    def closure(self):
        return self[4]

    @property
    def receiver(self):
        return self[5]

    @property
    def stack(self):
        return self[6:]

    @property
    def temps(self):
        cm = self.compiled_method
        return self.stack[cm.num_args: cm.num_temps]


@spurobject(3, class_index=CLOSURE_CLASS)
class BlockClosure(VariableSizedW):
    @property
    def outer_context(self):
        return self[0]

    @property
    def startpc(self):
        return self[1]

    @property
    def num_args(self):
        return self[2]

    @property
    def copied(self):
        return self[3:]
