from functools import lru_cache
import mmap
from .image_reader32 import Image, create_instance


class VM(object):
    bytecode_map = {}

    def __init__(self):
        self.mem = None
        self.image = None

    def open_image(self, image_file="/home/vince/dev/pharo/images/32bits/32bits.image"):
        with open(image_file, "r+b") as f:
            m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            self.image = Image(m)
            self.mem = self.image.mem
            self.image_file = image_file
            self.memory_allocator = MemoryAllocator(self.mem)

    def execute(self):
        try:
            self.current_context = self.initial_context()
            while self.current_context is not None:
                try:
                    self.current_context.execute()
                    self.current_context = self.current_context.previous_context
                except Continuate:
                    self.current_context = self.current_context.next_context
                except Pass:
                    pass
        except Quit:
            print('Evaluation finished')

    @property
    def first_active_process(self):
        inst = self.mem.special_object_array[3][1]
        active = inst.instvars[1]
        return active

    def initial_context(self):
        process = self.first_active_process
        context = process[1]
        method = context.instvars[3]
        cm = CompiledMethod(method.bytecode, method.literals, method)
        receiver = vmobject(context.instvars[5])
        return Context(compiled_method=cm, receiver=receiver, vm=self)


class MemoryAllocator(object):
    def __init__(self, memory):
        self.memory = memory
        self.first_address = 1 << 3


    def allocate(self, from_cls, size=0):
        address = self.first_address
        if size and isinstance(size, VMObject):
            size = size.obj
        if isinstance(from_cls, VMObject):
            from_cls = from_cls.obj
        instance = create_instance(address, from_cls, self.memory, array_size=size)
        self.first_address = instance.end_address
        return vmobject(instance)


class Continuate(Exception):
    pass


class Pass(Exception):
    pass


class BlockContinuate(Continuate):
    pass


class Finish(Exception):
    pass


class Quit(Exception):
    pass


class Context(object):
    # 0 sender
    # 1 pc
    # 2 stackp
    # 3 method
    # 4 closureOrNil
    # 5 receiver
    def __init__(
        self,
        compiled_method=None,
        receiver=None,
        temps=None,
        args=None,
        previous_context=None,
        initial_pc=0,
        vm=None,
        copied=None,
    ):
        self.stack = []
        self.previous_context = previous_context
        self.next_context = None
        self.vm = vm
        if previous_context:
            previous_context.next_context = self
            self.vm = previous_context.vm
        self.receiver = receiver
        self.compiled_method = compiled_method
        self.name = getattr(self.compiled_method, 'name', 'NoneYet')
        if temps is None:
            num_temps = compiled_method.obj.method_header.num_temps
            num_args = compiled_method.obj.method_header.num_args
            self.temporaries = [vmobject(self.vm.mem.nil)] * (num_temps + num_args)
        else:
            self.temporaries = temps
        if args:
            self.temporaries[:len(args)] = [vmobject(a) for a in args]
        self.args = args or []
        self.pc = initial_pc
        self.outer_context = None

    def push(self, value):
        self.stack.append(vmobject(value))

    def pop(self):
        return vmobject(self.stack.pop())

    def peek(self):
        return vmobject(self.stack[-1])

    def execute(self):
        name = self.name
        print(f"Executing '{name}'[{id(self)}]")
        execution_finished = False
        while not execution_finished:
            try:
                bytecode = self.compiled_method.preevaluate(self.pc)
                print(f"   PC {self.pc}[0x{bytecode.opcode:X}] {bytecode}")
                result = bytecode.execute(self)
                if result is not None:
                    print("intermediate result", result)
                    if self.previous_context:
                        self.previous_context.push(result)
                    execution_finished = True
                    print(f"Finishing '{name}'[{id(self)}]")
            except Finish:
                execution_finished = True
                print(f"Finishing normaly '{name}'[{id(self)}]")
            except IndexError:
                execution_finished = True
                print(f"Finishing on exception '{name}'[{id(self)}]")
                raise
            except KeyError as e:
                print("problem", self.compiled_method.raw_bytecode[self.pc])
                import ipdb; ipdb.set_trace()
                raise e
            except Continuate:
                print(f"Stoping '{name}'[{id(self)}] execution for going to '{self.next_context.name}'")
                raise


class CompiledMethod(object):
    bytecodes_map = VM.bytecode_map

    def __init__(self, raw_bytecode=None, literals=None, compiled_method=None, from_cls=None):
        self.raw_bytecode = raw_bytecode
        self.bytecodes = [None] * len(raw_bytecode)
        self.last_hash = 1
        self.literals = literals or []
        self.obj = compiled_method
        self.from_cls = from_cls

    def preevaluate(self, pc):
        current_bytecode = self.bytecodes[pc]
        if current_bytecode is not None:
            return current_bytecode
        opcode = self.raw_bytecode[pc]
        self.bytecodes[pc] = self.bytecodes_map[opcode](opcode)
        return self.bytecodes[pc]


class BlockClosure(CompiledMethod):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        return f"Closure({self.outer_context.name})"


@lru_cache()
def vmobject(o):
    return VMObject.vmobject(o)


class VMObject(object):
    main_objects = {}

    def __init__(self, spur_object):
        self.obj = spur_object
        # self.memory = spur_object.mem

    @classmethod
    @lru_cache()
    def vmobject(cls, spur_object):
        if isinstance(spur_object, cls):
            return spur_object
        return cls(spur_object)

    @property
    def address(self):
        return self.obj.address

    @property
    def is_true(self):
        return self.obj is self.obj.memory.true

    @property
    def is_false(self):
        return self.obj is self.obj.memory.false

    @property
    def is_nil(self):
        return self.obj is self.obj.memory.nil

    @property
    def class_(self):
        return vmobject(self.obj.class_)

    @property
    def instvars(self):
        return [self.vmobject(o) for o in self.obj.instvars]

    @property
    def array(self):
        return self.obj.array

    @property
    def method_dictionnary(self):
        return self.vmobject(self.instvars[1])

    @property
    def superclass(self):
        return self.instvars[0]

    def __getitem__(self, index):
        return self.vmobject(self.obj[index])

    @lru_cache(maxsize=256)
    # @profile
    def lookup(self, selector):
        md = self.method_dictionnary
        try:
            i = md.array.index(selector)
            method = md.instvars[1][i].obj
            print("Fetching", selector.as_text())
            return CompiledMethod(method.bytecode, method.literals, method, self)
        except ValueError:
            print("Not found", selector.as_text(), "for", self.obj)
            if self.superclass.obj is self.obj.memory.nil:
                print("Not found", selector, "for", self.obj)
                return None
            return self.superclass.lookup(selector)

    @lru_cache(maxsize=256)
    # @profile
    def lookup_byname(self, selector):
        nil_obj = self.obj.memory.nil
        md = self.method_dictionnary
        try:
            for i, s in enumerate(md.array):
                if s is not nil_obj:
                    t = s.as_text()
                    if t == selector:
                        break
            else:
                raise ValueError
            method = md.instvars[1][i].obj
            print("<*> Fetching by name", selector)
            c = CompiledMethod(method.bytecode, method.literals, method, self)
            c.name = selector
            return c
        except ValueError:
            print("Not found", selector, "for", self.obj)
            # if self.is_nil:
            #     print("Well... I'm nill, that's strange")
            #     import ipdb; ipdb.set_trace()
            #     superclass = self.class_
            # else:
            superclass = self.superclass
            if superclass.is_nil:
                print("Not found", selector, "for", self.obj)
                return None
            return superclass.lookup_byname(selector)

    def __repr__(self):
        return "{}({})".format(super().__repr__(), self.obj)



@lru_cache(maxsize=256)
def lookup(cls, selector):
    md = cls.method_dictionnary
    try:
        i = md.array.index(selector)
        method = md.instvars[1][i].obj
        print("Fetching", selector.as_text())
        return CompiledMethod(method.bytecode, method.literals, method, cls)
    except ValueError:
        print("Not found", selector.as_text(), "for", cls.obj)
        if cls.superclass.obj is cls.obj.memory.nil:
            print("Not found", selector, "for", cls.obj)
            return None
        return lookup(cls.superclass, selector)


@lru_cache(maxsize=256)
def lookup_byname(cls, selector):
    md = cls.method_dictionnary
    try:
        for i, s in enumerate(md.array):
            if s is not cls.obj.memory.nil and s.as_text() == selector:
                break
        else:
            raise ValueError
        method = md.instvars[1][i].obj
        print("<*> Fetching by name", selector)
        c = CompiledMethod(method.bytecode, method.literals, method, cls)
        c.name = selector
        return c
    except ValueError:
        print("Not found", selector, "for", cls.obj)
        if cls.is_nil:
            print("Well... I'm nill, that's strange")
            import ipdb; ipdb.set_trace()
            superclass = cls.class_
        else:
            superclass = cls.superclass
        if superclass.obj is cls.obj.memory.nil:
            print("Not found", selector, "for", cls.obj)
            return None
        return lookup_byname(superclass, selector)
