import struct
import time
from image64 import Image
from spurobjects.objects import *
from spurobjects.immediate import ImmediateInteger as integer
from bytecodes_new import ByteCodeMap


class VM(object):
    require_forward_switch = [131, 132, 133, *range(176, 256)]
    require_backward_switch = [*range(120, 126)]

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
            44: integer.create(6854880, self.memory)  # edenSize
        }
        self.current_context = self.initial_context()
        self.current_context.pc += 1
        self.nextWakeupUsecs = 0

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
        self.transfer_to(self.wake_highest_priority())

    def resume(self, process):
        active = self.active_process
        active_priority = active[2].value
        new_priority = process[2].value
        if new_priority > active_priority:
            print(f"<$> Sleep asked by {process.display()}")
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

    def fetch(self):
        self.check_interrupts()
        self.check_process_switch()
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
        # set all the mem to nil first
        nb_slots = stclass.inst_size + array_size
        nil = self.memory.nil
        slot_start = addr + 8
        for i in range(0, nb_slots * 8, 8):
            slot = self.memory[slot_start + i:slot_start + i + 8].cast("Q")
            slot[0] = nil.address
        instance = self.memory.object_at(addr)
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
        adapt = context.adapt_context()
        self._previous = adapt
        adapt._next = self

    @property
    def sender(self):
        return self.previous

    def adapt_context(self):
        return self

    def to_smalltalk_context(self, vm):
        if self.stcontext:
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

        self.stcontext = ctx
        return ctx

    def fetch_bytecode(self):
        return self.compiled_method.raw_data[self.pc]

    def push(self, obj):
        self.stack.append(obj)

    def pop(self):
        return self.stack.pop()

    def peek(self):
        return self.stack[-1]

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


def print_object(receiver):
    print("receiver", receiver.display())
    print("object type", receiver.__class__.__name__, "kind", receiver.kind)
    print("class", receiver.class_.name)
    print("slots")
    if receiver.kind in range(9, 24):
        for i in range(len(receiver)):
            if i > 0 and i % 8 == 0:
                print()
            print("", hex(receiver[i]), end="")
        print()
        print(f'text "{receiver.as_text()}"')
        return
    for i in range(len(receiver.slots)):
        print(f"{i:2}   ", receiver[i].display())
    if hasattr(receiver, "instvars"):
        print("instvar in slots")
        for i in range(len(receiver.instvars)):
            print(f"{i:2}   ", receiver.instvars[i].display())
    if hasattr(receiver, "array"):
        print("array in slots")
        for i in range(len(receiver.array)):
            print(f"{i:2}   ", receiver.array[i].display())



if __name__ == "__main__":
    vm = VM.new("Pharo8.0.image")
    from spurobjects import ImmediateFloat

    # for i in range(0, 50):
    #     e = vm.memory.class_table[i]
    #     if e is vm.memory.nil:
    #         continue
    #     print(i, e.name)

    i = integer.create(45, vm.memory)
    print(i.kind)
