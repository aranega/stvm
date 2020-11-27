from dataclasses import dataclass
import mmap
import struct
from spurobjects import SpurObject, ImmediateInteger, ImmediateFloat


class ByteChunk(object):
    def __init__(self, size, start=0, after=None):
        self.start = start
        self.size = size
        if after:
            self.start = after.start + after.size

    def __get__(self, obj, objtype=None):
        return int.from_bytes(obj.header[self.start: self.start + self.size], byteorder="little")


class SpurMemoryHandler(object):
    special_array = {
        "nil": 0,
        "false": 1,
        "true": 2,
        "smallinteger": 5,
        "bytestring": 6,
        "array": 7,
        "context_class": 10,
        "largepositiveint": 13,
        "character": 19,
        "dnuSelector": 20,
        "special_symbols": 23,
        "block_closure_class": 36,
    }
    def __init__(self, memory):
        self.memory = memory
        self.cache = {}

    def init_const(self):
        for name, pos in self.special_array.items():
            setattr(self.memory, name, self.special_object_array[pos])
        setattr(self.memory, "class_table", self.class_table)
        setattr(self.memory, "special_object_array", self.special_object_array)
        setattr(self.memory, "smallfloat64", self.class_table[4])

    def init_smallints(self):
        for i in range(-255, 255):
            imm = ImmediateInteger.create(i, self.memory)
            self.cache[imm.address] = imm

    @property
    def special_object_array(self):
        return self.object_at(self.memory.special_object_oop)

    def object_at(self, address, class_table=False):
        if address in self.cache:
            return self.cache[address]
        address_kind = address & 0x07
        if address_kind == 0:
            obj = SpurObject.create(address, self.memory, class_table=class_table)
        elif address_kind == 1:
            obj = ImmediateInteger(address, self.memory)
        elif address_kind == 2:
            import ipdb; ipdb.set_trace()
        elif address_kind == 3:
            import ipdb; ipdb.set_trace()
        elif address_kind == 4:
            obj = ImmediateFloat(address, self.memory)

        self.cache[address] = obj
        return obj

    @property
    def free_list(self):
        # self.true.next_object
        true_position = self.special_array["true"]
        return self.special_object_array[true_position].next_object

    @property
    def class_table(self):
        return self.object_at(self.free_list.end_address + 8, class_table=True)


class VMMemory(object):
    def __init__(self, image):
        self.image = image
        old = image.old_base_address
        header_end = image.header_size
        objects = image.map[header_end:]
        self.mem = memoryview(bytearray(b'0' * (old + len(objects))))
        self.mem[old:] = objects
        self.handler = SpurMemoryHandler(self)
        self.handler.init_const()
        self.handler.init_smallints()

    def __getitem__(self, i):
        return self.mem[i]

    def __setitem__(self, i, value):
        self.mem[i] = value

    @property
    def special_object_oop(self):
        return self.image.special_object_oop

    def object_at(self, address):
        return self.handler.object_at(address)


class Image(object):
    image_version = ByteChunk(size=4)
    header_size = ByteChunk(size=4, after=image_version)
    data_size = ByteChunk(size=8, after=header_size)
    old_base_address = ByteChunk(size=8, after=data_size)
    special_object_oop = ByteChunk(size=8, after=old_base_address)
    last_hash = ByteChunk(size=8, after=special_object_oop)
    saved_window_size = ByteChunk(size=8, after=last_hash)
    header_flags = ByteChunk(size=8, after=saved_window_size)
    extra_VM_memory = ByteChunk(size=4, after=header_flags)
    hdr_num_stack_pages = ByteChunk(size=2, after=extra_VM_memory)
    hdr_eden_bytes = ByteChunk(size=4, after=hdr_num_stack_pages)
    hdr_max_ext_sem_tab_size = ByteChunk(size=2, after=hdr_eden_bytes)
    second_unknown_short = ByteChunk(size=4, after=hdr_max_ext_sem_tab_size)  # TODO: check
    first_seg_size = ByteChunk(size=8, after=second_unknown_short)

    def __init__(self, filename, load=True):
        self.filename = filename
        self.map = None
        self.header = None
        self.object_space = None
        self.handler = SpurMemoryHandler(self)
        if load:
            self.load()

    def load(self):
        with open(self.filename, mode="br") as f:
            memory = mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ)
            self.map = memoryview(memory)
            self.header = self.map[:80]
            self.object_space = self.map[self.header_size:]

    def __getitem__(self, i):
        offset = self.old_base_address
        objects = self.object_space
        if isinstance(i, slice):
            return objects[i.start - offset : i.stop - offset : i.step]
        return objects[i - offset]

    def as_memory(self):
        return VMMemory(self)


if __name__ == "__main__":
    i = Image('Pharo8.0.image')
    mem = i.as_memory()
    e = mem.smallinteger
    # print(mem.object_at(e[1].array[3]))
    print(e[1].class_.inst_size)
    m = e[1][1][3]
    print(e[1].array_at(3))
    print(m[1])

    e = mem.special_object_array
    for _ in range(7278):
        e = e.next_object

    print(e)
