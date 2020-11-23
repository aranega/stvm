from image64 import Image
from spurobjects.objects import *
from bytecodes_new import ByteCodeMap


class VM(object):
    require_forward_switch = [*range(176, 256)]
    require_backward_switch = [*range(121, 125)]
    def __init__(self, memory, bytecodes_map=ByteCodeMap, debug=False):
        self.memory = memory
        self.debug = debug
        self.bytecodes_map = bytecodes_map()
        self.current_context = self.initial_context()

    @classmethod
    def new(cls, file_name):
        return cls(Image(file_name).as_memory())

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
        return Context.from_smalltalk_context(context)

    def fetch(self):
        return self.current_context.fetch_bytecode()

    def decode_execute(self, bytecode):
        result = self.bytecodes_map.execute(bytecode, self.current_context, self)
        context = self.current_context
        if bytecode in self.require_forward_switch:
            self.current_context = context.next
        elif context.from_primitive and context.primitive_success:
            context.previous.push(context.pop())
            self.current_context = context.previous
        elif bytecode in self.require_backward_switch:
            context.previous.push(context.pop())
            self.current_context = context.previous
        return result

    def lookup(self, cls, selector):
        nil = self.memory.nil
        while cls != nil:
            method_dict = cls[1]
            try:
                index = method_dict.array.index(selector)
                return method_dict.instvars[1][index]
            except ValueError:
                # deal with super classes
                cls = cls[0]
        # send dnu


class Context(object):
    def __init__(self, receiver, compiled_method):
        self.receiver = receiver
        self.compiled_method = compiled_method
        self.pc = 0
        self.outer_context = None
        self.pc = compiled_method.initial_pc
        self._previous = None
        self._next = None
        self.stack = self._pre_setup(compiled_method)
        self.primitive_success = True
        self.from_primitive = False

    def _pre_setup(self, compiled_method):
        nil = compiled_method.memory.nil
        num_args = compiled_method.num_args
        num_temps = compiled_method.num_temps
        stack = [nil] * num_args
        stack.extend([nil] * num_temps)
        return stack

    @property
    def args(self):
        return self.stack[:self.compiled_method.num_args]

    @property
    def temps(self):
        cm = self.compiled_method
        return self.stack[cm.num_args: cm.num_args + cm.num_temps]

    @property
    def next(self):
        return self._next

    @next.setter
    def next(self, context):
        self._next = context
        context._previous = self

    @property
    def previous(self):
        return self._previous

    @previous.setter
    def previous(self, context):
        self._previous = context
        context._next = self

    @classmethod
    def from_smalltalk_context(cls, context):
        return cls(context.instvars[5], context.instvars[3])

    def fetch_bytecode(self):
        return self.compiled_method.raw_data[self.pc]

    def push(self, obj):
        self.stack.append(obj)

    def pop(self):
        return self.stack.pop()

    def peek(self):
        return self.stack[-1]


if __name__ == "__main__":
    vm = VM.new("Pharo8.0.image")
    vm.run()
    context = vm.initial_context()
    code = vm.fetch()
    vm.decode_execute(code)
    print(context.stack)
