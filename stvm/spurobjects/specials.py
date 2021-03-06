from .objects import VariableSizedW, SpurObject, FixedSized
from .immediate import ImmediateInteger as integer

MESSAGE_CLASS = 35
CONTEXT_CLASS = 36
CLOSURE_CLASS = 37
FULLCLOSURE_CLASS = 38
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

    def is_unwind(self):
        return self[3].primitive == 198

    def is_handler_or_signaling(self):
        return self[3].primitive == 199

    def terminate(self):
        self.slots[0] = self.memory.nil
        self.slots[1] = self.memory.nil

    def to_smalltalk_context(self, vm):
        return self

    def update_context(self):
        if not self.vm_context:
            return self.adapt_context()
        native_ctx = self.vm_context
        if self.pc.value == native_ctx.pc:
            # nothing changed as the PC didn't move
            return native_ctx
        # update pc
        self[1] = integer.create(native_ctx.pc, self.memory)
        # update stackp
        stackp = len(native_ctx.stack)
        self[2] = integer.create(stackp, self.memory)
        # update stack
        for i, v in enumerate(native_ctx.stack):
            self.stack[i] = v
        # update sender
        if native_ctx.previous:
            self[0] = native_ctx.sender.stcontext
        # update compiled method
        self[3] = native_ctx.compiled_method
        # update receiver
        self[5] = native_ctx.receiver
        # update closure
        self[4] = native_ctx.closure

    def adapt_context(self):
        if self.vm_context:
            self.vm_context.update_context()
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
        context.stcontext = self
        self.vm_context = context
        return context

    def pop(self):
        return self.adapt_context().pop()

    def push(self, v):
        self.adapt_context().push(v)

    def fetch_bytecode(self):
        return self.adapt_context().fetch_bytecode()

    def peek(self):
        return self.adapt_context().peek()

    @property
    def home(self):
        return self.adapt_context().home


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

    @property
    def home(self):
        return self.outer_context.home

    def basic_at(self, i):
        return self.slots[i]


@spurobject(1, class_index=MESSAGE_CLASS)
class Message(FixedSized):
    @property
    def selector(self):
        return self[0]

    @property
    def args(self):
        return self[1]

    @property
    def lookup_class(self):
        return self[2]

    @selector.setter
    def selector(self, s):
        self[0] = s

    @args.setter
    def args(self, array):
        self[1] = array

    @lookup_class.setter
    def lookup_class(self, lookup):
        self[2] = lookup


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
