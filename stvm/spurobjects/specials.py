from .objects import VariableSizedW, SpurObject
from .immediate import ImmediateInteger as integer

CONTEXT_CLASS = 36
CLOSURE_CLASS = 37
SEMAPHORE_CLASS = 48


def spurobject(t, class_index):
    def func(c):
        SpurObject.special_subclasses[(t, class_index)] = c
        return c
    return func



@spurobject(3, class_index=CONTEXT_CLASS)
class Context(VariableSizedW):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vm_context = None

    @property
    def sender(self):
        return self[0]

    @property
    def pc(self):
        return self[1]

    @property
    def stackp(self):
        return self[2]

    @stackp.setter
    def stackp(self, value):
        self[2] = value

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

    @property
    def args(self):
        cm = self.compiled_method
        return self.stack[: cm.num_args]

    def to_smalltalk_context(self, vm):
        return self

    def adapt_context(self):
        if self.vm_context:
            return self.vm_context
        from ..vm import VMContext
        memory = self.memory
        cm = self[3]
        context = VMContext(self[5], cm, memory)
        stackp = self[2]
        context.stack[:] = self.array[:stackp.value]
        context.pc = self[1].value
        if self[0] is not memory.nil:
            context.previous = self[0]
        else:
            context._previous = self[0]
        self.vm_context = context
        return context

    def pop(self):
        self.adapt_context().pop()

    def push(self, v):
        self.adapt_context().push(v)


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


# @spurobject(1, class_index=SEMAPHORE_CLASS)
# class Semaphore(FixedSized):
#     def add_last_link(self, link):
#         if self.is_empty():
#             self.slots[0] = link
#         else:
#             last_link = self.slots[1]
#             last_link.slots[0] = link
#         self.slots[1] = link
#         link.slots[3] = self
#
#     def is_empty(self):
#         return self[0] is self.memory.nil
#
#     def remove_first_link(self):
#         nil = self.memory.nil
#         first = self[0]
#         last = first
#         if last is first:
#             self.slots[0] = nil
#             self.slots[1] = nil
#         else:
#             self.slots[0] = first[0]
#         first.slots[0] = nil
#         return first
