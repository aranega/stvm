import struct
from image64 import Image
from spurobjects.objects import *
from spurobjects.immediate import ImmediateInteger
from bytecodes_new import ByteCodeMap


class VM(object):
    require_forward_switch = [131, 132, 133, *range(176, 256)]
    require_backward_switch = [*range(120, 125)]
    def __init__(self, image, bytecodes_map=ByteCodeMap, debug=False):
        self.image = image
        self.memory = image.as_memory()
        self.allocator = MemoryAllocator(self.memory)
        self.debug = debug
        self.bytecodes_map = bytecodes_map()
        self.current_context = self.initial_context()
        self.current_context.pc += 1

    @classmethod
    def new(cls, file_name):
        return cls(Image(file_name))

    def run(self):
        ...

    @property
    def active_process(self):
        instance = self.memory.special_object_array[3][1]
        active_process = instance[1]
        return active_process

    def initial_context(self):
        process = self.active_process
        context = process[1]
        return Context.from_smalltalk_context(context, self)

    def fetch(self):
        return self.current_context.fetch_bytecode()

    def decode_execute(self, bytecode):
        result = self.bytecodes_map.execute(bytecode, self.current_context, self)
        context = self.current_context
        if bytecode in self.require_forward_switch and self.current_context.next:
            self.current_context = context.next
        elif context.from_primitive and context.primitive_success:
            if context.next:
                self.current_context = context.next
            else:
                context.previous.push(context.pop())
                self.current_context = context.previous
                self.current_context.next = None
        elif bytecode in self.require_backward_switch:
            context.previous.push(context.pop())
            self.current_context = context.previous
            self.current_context.next = None
        return result

    def lookup(self, cls, selector):
        nil = self.memory.nil
        original_class = cls
        while cls != nil:
            method_dict = cls[1]
            try:
                index = method_dict.array.index(selector)
                return method_dict.instvars[1][index]
            except ValueError:
                # deal with super classes
                cls = cls[0]
        import ipdb; ipdb.set_trace()
        return self.lookup(original_class, self.memory.dnuSelector)

    def allocate(self, stclass, array_size=0):
        return self.allocator.allocate(stclass, array_size)


class MemoryAllocator(object):
    def __init__(self, memory):
        self.memory = memory
        self.start = 1 << 3
        self.current = self.start

    def allocate(self, stclass, array_size=0):
        addr = self.current
        header = self.create_header(stclass, array_size)
        self.memory[addr:addr + 8] = header
        instance = self.memory.object_at(addr)
        nil = self.memory.nil
        for i in range(instance.number_of_slots):
            instance.slots[i] = nil
        self.current = instance.next_object.end_address + 8
        return instance


    def create_header(self, stclass, array_size=0):
        nb_slots = stclass.inst_size + array_size
        format = stclass.inst_format
        sub1, sub2 = 0, 0
        sub2 = (nb_slots << 24)
        sub1 = ((format & 0x1F)  << 24)
        sub1 = sub1 | stclass.identity_hash  # class index
        header = struct.pack("Q", (sub2 << 32) | sub1)
        return header


class Context(object):
    def __init__(self, receiver, compiled_method, vm):
        self.vm = vm
        nil = self.vm.memory.nil
        self.receiver = receiver
        self.compiled_method = compiled_method
        self.pc = 0
        self.outer_context = nil
        self.pc = compiled_method.initial_pc
        self._previous = None
        self._next = None
        self.stack = self._pre_setup(compiled_method)
        self.primitive_success = True
        self.from_primitive = False
        self.kind = 0

    def _pre_setup(self, compiled_method):
        nil = compiled_method.memory.nil
        num_args = compiled_method.num_args
        self.start_args = 0
        self.start_temps = num_args
        num_temps = compiled_method.num_temps
        stack = [nil] * num_temps
        return stack

    @property
    def args(self):
        return self.stack[:self.compiled_method.num_args]

    @property
    def temps(self):
        cm = self.compiled_method
        return self.stack[cm.num_args: cm.num_temps]

    @property
    def next(self):
        return self._next

    @next.setter
    def next(self, context):
        # if self._next:
        #     self._next._previous = None
        self._next = context
        if context:
            context._previous = self
            # context.sender = self.receiver

    @property
    def previous(self):
        return self._previous

    @previous.setter
    def previous(self, context):
        self._previous = context
        context._next = self

    @property
    def sender(self):
        return self.previous

    @classmethod
    def from_smalltalk_context(cls, st_context, vm):
        if st_context is st_context.memory.nil:
            return st_context.memory.nil
        cm = st_context.instvars[3]
        context = cls(st_context.instvars[5], cm, vm)
        stackp = st_context[2]
        context.stack[:] = st_context.array[:stackp.value]
        context.pc = st_context[1].value
        if st_context[0] is not st_context.memory.nil:
            context.previous = st_context[0]
        else:
            context._previous = st_context[0]
        return context

    def to_smalltalk_context(self):
        memory = self.vm.memory
        stclass = self.class_
        nil = memory.nil
        frame_size = self.compiled_method.frame_size
        ctx = self.vm.allocate(stclass, array_size=frame_size)
        if self.sender != nil:
            if isinstance(self.sender, (Context, BlockClosure)):
                ctx.slots[0] = self.sender.to_smalltalk_context()
            else:
                ctx.slots[0] = self.sender
        else:
            ctx.slots[0] = nil
        ctx.slots[1] = ImmediateInteger.create(self.pc, memory)
        ctx.slots[2] = ImmediateInteger.create(len(self.stack), memory)
        ctx.slots[3] = self.compiled_method
        if self.outer_context != nil:
            if isinstance(self.outer_context, (Context, BlockClosure)):
                ctx.slots[4] = self.outer_context.to_smalltalk_context()
            else:
                ctx.slots[4] = self.outer_context
        else:
            ctx.slots[4] = nil

        ctx.slots[5] = self.receiver
        for i, v in enumerate(self.stack):
            ctx.slots[6 + i] = v
        return ctx

    def fetch_bytecode(self):
        return self.compiled_method.raw_data[self.pc]

    def push(self, obj):
        self.stack.append(obj)

    def pop(self):
        return self.stack.pop()

    def peek(self):
        return self.stack[-1]

    def block_closure(self, start):
        return BlockClosure(self, start)

    def display(self):
        cm = self.compiled_method
        return f"<context {hex(id(self))} on {cm.selector.as_text()}>"

    def __getitem__(self, i):
        return self.slots[i]

    @property
    def slots(self):
        # FAKE STACK/SLOTS
        mem = self.compiled_method.memory
        pc = ImmediateInteger.create(self.pc, mem)
        stakfp = ImmediateInteger.create(len(self.stack), mem)
        outer = self.outer_context
        if self.outer_context is None:
            outer = mem.nil
        stack = [self.sender, pc, stakfp, self.compiled_method, outer, self.receiver, *self.stack]
        return stack

    @property
    def class_(self):
        return self.receiver.memory.context_class


class BlockClosure(object):
    def __init__(self, context, start):
        self.outer_context = context
        self.memory = context.vm.memory
        cm = context.compiled_method
        info = cm.raw_data[start + 1]
        self.num_copied = (info & 0xF0) >> 4
        self.num_args = info & 0x0F
        size = int.from_bytes(cm.raw_data[start + 2: start + 4], byteorder="big")

        copied = [self.outer_context.pop() for i in range(self.num_copied)]
        copied.reverse()
        self.start = start + 4
        self.pc = self.start
        self.size = size

        nil = cm.memory.nil
        # num_temps = compiled_method.num_temps
        stack = [nil] * self.num_args
        stack.extend(copied)
        # stack.extend([nil] * num_temps)
        self.stack = stack

    def display(self):
        return f"<closure [{self.start}-{self.start + self.size - 1}] <args={self.num_args}, copied={self.num_copied}>>"

    @property
    def slots(self):
        # FAKE STACK/SLOTS
        mem = self.outer_context.vm.memory
        outer = self.outer_context
        pc = ImmediateInteger.create(self.pc, mem)
        num_args = ImmediateInteger.create(self.num_args, mem)
        stack = [outer, pc, num_args, *self.stack]
        return stack

    @property
    def class_(self):
        return self.outer_context.vm.memory.block_closure_class

if __name__ == "__main__":
    vm = VM.new("Pharo8.0.image")
    from spurobjects import ImmediateFloat

    # 49513832
    # 9136902924009262292
    # 567453553048682496
    print(hex(567453553048682496))
    j = ImmediateFloat(0x7e00000000000004, vm.memory)
    print(j)
    j = ImmediateFloat.create(0.9, vm.memory)
    print(j)
    print(j.address)
