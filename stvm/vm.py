import struct
import time
from math import ceil
from .image64 import Image
from .spurobjects.objects import *
from .spurobjects import ImmediateInteger as integer
from .bytecodes import ByteCodeMap


class VM(object):

    def __init__(self, image, bytecodes_map=ByteCodeMap, debug=False):
        self.image = image
        self.memory = image.as_memory()
        self.allocator = MemoryAllocator(self.memory)
        self.debug = debug
        self.bytecodes_map = bytecodes_map()
        self.new_process_waiting = False
        self.new_process = None
        self.semaphores = []
        self.semaphore_index = -1
        self.params = {
            40: integer.create(8, self.memory),  # word size
            44: integer.create(6854880, self.memory),  # edenSize
            48: integer.create(0, self.memory) # various headers?
        }
        self.current_context = self.initial_context()
        self.current_context.pc += 1
        self.nextWakeupUsecs = 0
        self.method_cache = {}
        self.opened_files = {}
        self.last_hash = image.last_hash

    def add_last_link_list(self, link, linkedlist):
        if self.is_empty_list(linkedlist):
            linkedlist.slots[0] = link
        else:
            last_link = linkedlist.slots[1]
            last_link.slots[0] = link
        linkedlist.slots[1] = link
        link.slots[3] = linkedlist

    def is_empty_list(self, linkedlist):
        return linkedlist[0] is self.memory.nil

    def remove_first_link_list(self, linkedlist):
        nil = self.memory.nil
        first = linkedlist[0]
        last = first
        if last is first:
            linkedlist.slots[0] = nil
            linkedlist.slots[1] = nil
        else:
            linkedlist.slots[0] = first[0]
        first.slots[0] = nil
        return first

    @property
    def scheduler(self):
        return self.memory.special_object_array[3][1]

    @property
    def active_process(self):
        if self.new_process_waiting:
            return self.new_process
        return self.scheduler[1]

    def transfer_to(self, process):
        self.new_process_waiting = True
        self.new_process = process

    def asynchronous_signal(self, semaphore):
        self.semaphore_index += 1
        self.semaphores.append(semaphore)

    def synchronous_signal(self, sem):
        if self.is_empty_list(sem):
            excessSignals = sem.slots[2].value
            sem.slots[2] = integer.create(excessSignals + 1, self.memory)
            return
        self.resume(self.remove_first_link_list(sem))

    def wake_highest_priority(self):
        process_lists = self.scheduler[0]
        priority = len(process_lists)
        process_list = process_lists[priority - 1]
        while self.is_empty_list(process_list):
            priority -= 1
            process_list = process_lists[priority]
        return self.remove_first_link_list(process_list)

    def suspend_active(self):
        print(f"<$> Suspend active context")
        self.transfer_to(self.wake_highest_priority())

    def resume(self, process):
        active = self.active_process
        active_priority = active[2].value
        new_priority = process[2].value
        if new_priority > active_priority:
            print(f"<$> Sleep asked for {active.display()} by {process.display()}")
            self.sleep(active)
            self.transfer_to(process)
        else:
            # print(f"<$> Sleep asked by {process.display()}")
            self.sleep(process)

    def wait(self, sem):
        excessSignals = sem[2].value
        if excessSignals > 0:
            sem.slots[2] = integer.create(excessSignals - 1, self.memory)
            return
        self.add_last_link_list(self.active_process, sem)
        self.suspend_active()

    def sleep(self, process):
        print(f"<*> Process sleep  {process.display()}")
        priority = process[2].value
        process_lists = self.scheduler[0]
        process_list = process_lists[priority - 1]
        self.add_last_link_list(process, process_list)

    def check_process_switch(self):
        while self.semaphore_index >= 0:
            self.synchronous_signal(self.semaphores[self.semaphore_index])
            self.semaphore_index -= 1
        if self.new_process_waiting:
            self.new_process_waiting = False
            active = self.active_process
            print(f"<*> Process switch {active.display()} to {self.new_process.display()}")
            active.slots[1] = self.current_context.to_smalltalk_context(self)
            self.scheduler.slots[1] = self.new_process
            self.current_context = self.new_process[1].adapt_context()

    @classmethod
    def new(cls, file_name):
        return cls(Image(file_name))

    def run(self):
        ...

    def initial_context(self):
        process = self.active_process
        context = process[1]
        return context.adapt_context()
        # return VMContext.from_smalltalk_context(context, self)

    def check_interrupts(self):
        memory = self.memory
        if self.nextWakeupUsecs != 0:
            now = int(round(time.time() * 1000000))
            if now >= self.nextWakeupUsecs:
                self.nextWakeupUsecs = 0
                sema = memory.timer_semaphore
                if sema is not memory.nil:
                    self.asynchronous_signal(sema)
                    print(f"<*> Signal timer semaphore {sema.display()}")

    def low_fetch(self):
        return self.current_context.fetch_bytecode()

    def fetch(self):
        # self.check_process_switch()
        # self.check_interrupts()
        return self.low_fetch()

    def decode_execute(self, bytecode):
        result = self.bytecodes_map.execute(bytecode, self.current_context, self)
        return result

    def activate_context(self, context):
        self.current_context = context

    def lookup(self, cls, selector):
        cple = (cls, selector)
        if cple in self.method_cache:
            return self.method_cache[cple]
        nil = self.memory.nil
        original_class = cls
        while cls != nil:
            method_dict = cls[1]
            try:
                index = method_dict.array.index(selector)
                method = method_dict.instvars[1][index]
                self.method_cache[cple] = method
                self.method_cache[(cls, selector)] = method
                return method
            except ValueError:
                # deal with super classes
                cls = cls[0]
        # raise DebugException(f"Method {selector.as_text()} not found in {original_class.display()}")
        # import ipdb; ipdb.set_trace()
        return self.lookup(original_class, self.memory.dnuSelector)

    def allocate(self, stclass, array_size=0, data_len=0):
        return self.allocator.allocate(stclass, array_size, data_len)


class DebugException(Exception):
    ...


class MemoryAllocator(object):
    def __init__(self, memory):
        self.memory = memory
        self.start = 1 << 3
        self.current = self.start
        self.limit = self.memory.special_object_array.address

    def allocate(self, stclass, array_size=0, data_len=0):
        addr = self.current
        header, nb_slots = self.create_header(stclass, array_size, data_len)
        if nb_slots >= 255:
            addr = addr + 8
            self.memory[addr-8:addr-4] = struct.pack("I", nb_slots)
        self.memory[addr:addr + 8] = header
        # set all the mem to nil first
        self.init_rawslots(self.memory, addr, nb_slots)
        instance = self.memory.object_at(addr)
        if instance.kind in range(9, 24):
            self.init_zero(instance)
        self.current = instance.next_object.end_address + 8
        return instance

    @staticmethod
    def init_rawslots(memory, addr, nb_slots):
        nil = memory.nil
        slot_start = addr + 8
        for i in range(0, nb_slots * 8, 8):
            slot = memory[slot_start + i:slot_start + i + 8].cast("Q")
            slot[0] = nil.address

    @staticmethod
    def init_zero(instance):
        memory = instance.memory
        nb_values = len(instance.raw_slots)
        instance.raw_slots[:] = b'\x00' * nb_values

    def create_header(self, stclass, array_size=0, data_len=0):
        format = stclass.inst_format
        if format in range(9, 24) and data_len == 0:
            data_len = array_size
        if data_len:
            bits = Indexable._bits[format - 9]
            array_size = ceil(data_len / bits)
            data_per_row = 64 // bits
            format += (data_per_row - (data_len % data_per_row)) % data_per_row
        total_slots = stclass.inst_size + array_size
        slots = total_slots if total_slots < 255 else 255
        sub1, sub2 = 0, 0
        sub2 = (slots << 24)
        sub1 = ((format & 0x1F)  << 24)
        sub1 = sub1 | stclass.identity_hash  # class index
        header = struct.pack("<Q", (sub2 << 32) | sub1)
        return (header, total_slots)


class VMContext(object):
    def __init__(self, receiver, compiled_method, memory):
        # self.vm = vm
        self.memory = memory
        self.stcontext = None
        nil = memory.nil
        self.receiver = receiver
        self.compiled_method = compiled_method
        self.pc = 0
        self.closure = nil
        self.pc = compiled_method.initial_pc
        self._previous = None
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
    def previous(self):
        return self._previous

    @previous.setter
    def previous(self, context):
        try:
            adapt = context.adapt_context()
            self._previous = adapt
        except Exception:
            import ipdb; ipdb.set_trace()
            self._previous = self.memory.nil

    @property
    def sender(self):
        return self.previous

    def adapt_context(self):
        return self

    def to_smalltalk_context(self, vm):
        if self.stcontext:
            self.stcontext.update_context()
            return self.stcontext
        memory = vm.memory
        stclass = self.class_
        nil = memory.nil
        frame_size = self.compiled_method.frame_size
        ctx = vm.allocate(stclass, array_size=frame_size)
        if self.sender != nil:
            if isinstance(self.sender, VMContext):
                ctx.slots[0] = self.sender.to_smalltalk_context(vm)
            else:
                ctx.slots[0] = self.sender
        else:
            ctx.slots[0] = nil
        ctx.slots[1] = integer.create(self.pc, memory)
        ctx.slots[2] = integer.create(len(self.stack), memory)
        ctx.slots[3] = self.compiled_method
        if self.closure != nil:
            if isinstance(self.closure, VMContext):
                ctx.slots[4] = self.closure.to_smalltalk_context(vm)
            else:
                ctx.slots[4] = self.closure
        else:
            ctx.slots[4] = nil

        ctx.slots[5] = self.receiver
        for i, v in enumerate(self.stack):
            ctx.stack[i] = v

        ctx.vm_context = self
        self.stcontext = ctx
        return ctx

    def update_context(self):
        ctx = self.stcontext
        if self.pc == ctx.pc.value:
            # nothing changed as the PC didn't move
            return ctx
        # update pc
        self.pc = ctx.pc.value
        # update stack
        stackp = ctx.stackp.value
        self.stack[:] = ctx.array[:stackp]
        # update sender
        self.previous = ctx.sender
        # update compiled method
        self.compiled_method = ctx.compiled_method
        # update receiver
        self.receiver = ctx.receiver
        # update closure
        self.closure = ctx.closure

    def fetch_bytecode(self):
        return self.compiled_method.raw_data[self.pc]

    def push(self, obj):
        self.stack.append(obj)

    def pop(self):
        return self.stack.pop()

    def peek(self):
        return self.stack[-1]

    @property
    def home(self):
        if self.closure is None or self.closure is self.memory.nil:
            return self
        return self.closure.home

    def display(self):
        cm = self.compiled_method
        return f"<context {hex(id(self))} on {cm.selector.as_text()}>"

    def __getitem__(self, i):
        return self.slots[i]

    @property
    def slots(self):
        # FAKE STACK/SLOTS
        mem = self.compiled_method.memory
        pc = integer.create(self.pc, mem)
        stakfp = integer.create(len(self.stack), mem)
        outer = self.closure
        if outer is None:
            outer = mem.nil
        stack = [self.sender, pc, stakfp, self.compiled_method, outer, self.receiver, *self.stack]
        return stack

    @property
    def class_(self):
        return self.memory.context_class
