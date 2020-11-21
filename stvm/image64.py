from dataclasses import dataclass
import mmap
import struct


class ByteChunk(object):
    def __init__(self, size, start=0, after=None):
        self.start = start
        self.size = size
        if after:
            self.start = after.start + after.size

    def __get__(self, obj, objtype=None):
        return int.from_bytes(obj.header[self.start: self.start + self.size], byteorder="little")


class Memory(object):
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
    }
    def __init__(self):
        super().__init__()
        self.cache = {}

    @property
    def special_object_array(self):
        return self.object_at(self.image.special_object_oop)

    def object_at(self, address, class_table=False):
        if address in self.cache:
            return self.cache[address]
        address_kind = address & 0x07
        if address_kind == 0:
            obj = SpurObject.create(address, self, class_table=class_table)
        elif address_kind == 1:
            obj = ImmediateInteger(address, self)
        elif address_kind == 2:
            import ipdb; ipdb.set_trace()
        elif address_kind == 3:
            import ipdb; ipdb.set_trace()
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


class VMMemory(Memory):
    def __init__(self, image):
        super().__init__()
        self.image = image
        old = image.old_base_address
        header_end = image.header_size
        objects = image.map[header_end:]
        self.mem = memoryview(bytearray(b'0' * (old + len(objects))))
        self.mem[old:] = objects
        self.init_const()

    def __getitem__(self, i):
        return self.mem[i]

    def init_const(self):
        for name, pos in self.special_array.items():
            setattr(self, name, self.special_object_array[pos])


class Image(Memory):
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
        super().__init__()
        self.filename = filename
        self.map = None
        self.header = None
        self.object_space = None
        if load:
            self.load()

    def load(self):
        with open(self.filename, mode="br") as f:
            memory = mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ)
            self.map = memoryview(memory)
            self.header = self.map[:80]
            self.object_space = self.map[self.header_size:]
            self.memory = VMMemory(self)

    def __getitem__(self, i):
        offset = self.old_base_address
        objects = self.object_space
        if isinstance(i, slice):
            return objects[i.start - offset : i.stop - offset : i.step]
        return objects[i - offset]


class SpurObject(object):
    header_size = 8
    def __init__(self, address, memory):
        self.memory = memory
        self._address = address
        self.update(address)

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, value):
        self.update(value)
        self._address = value

    def update(self, new_address):
        old = self._address
        try:
            del self.memory.cache[old]
        except Exception:
            ...

        address = new_address
        mem = self.memory
        header = self.memory[address:address + 8]
        _, nb_slots = self.decode_basicinfo(header)
        if nb_slots > 254:
            nb_slots = mem[address - 8 : address - 4].cast("I")[0]
        self.raw_object = mem[address:address + self.header_size + (nb_slots * 8)]
        self.header = self.raw_object[:8]
        self.header1 = self.header[:4]
        self.header2 = self.header[4:8]
        self.raw_slots = self.raw_object[8:]
        self.slots = [self.raw_slots[i:i + 8] for i in range(0, nb_slots * 8, 8)]

    @classmethod
    def create(cls, address, memory, class_table=False):
        header = memory[address:address + 8]
        obj_format, _ = cls.decode_basicinfo(header)
        SpurClass = ClassTable if class_table else cls.spur_implems[obj_format]
        obj = SpurClass(address, memory)
        return obj

    @property
    def end_address(self):
        header_size = 8
        slots_size = max(self.number_of_slots, 1) * 8
        basic_size = header_size + slots_size
        padding = basic_size % 8
        return self.address + basic_size + padding

    @property
    def next_object(self):
        new_object_address = self.end_address + 8
        address = self.address
        header = self.memory[address:address + 8]
        _, nb_slots = self.decode_basicinfo(header)
        if nb_slots == 0xFF:
            return self.memory.object_at(new_object_address)
        return self.memory.object_at(self.end_address)

    @staticmethod
    def decode_basicinfo(header):
        f, g = header.cast("I")
        number_of_slots=(g & 0xFF000000) >> 24
        object_format=(f & 0x1F000000) >> 24
        return (object_format, number_of_slots)

    def __getitem__(self, index):
        return self.memory.object_at(self.slots[index].cast("Q")[0])

    @property
    def h1(self):
        return self.header1.cast("I")[0]

    @property
    def h2(self):
        return self.header2.cast("I")[0]

    @property
    def class_index(self):
        return self.h1 & 0x3FFFFF

    @property
    def inst_size(self):
        return self[2] & 0xFFFF

    @property
    def number_of_slots(self):
        adr = self.address
        mem = self.memory
        n = (self.h2 & 0xFF000000) >> 24
        return n if n < 255 else mem[adr - 8 : adr - 4].cast("I")[0]

    @property
    def is_immutable(self):
        return (self.h1 & 0x600000) > 0

    @property
    def object_format(self):
        return (self.h1 & 0x1F000000) >> 24

    @property
    def is_remembered(self):
        return (self.h1 & 0x20000000) > 0

    @property
    def is_pinned(self):
        return (self.h1 & 0x40000000) > 0

    @property
    def class_(self):
        return self.memory.class_table[self.class_index]


class VariableSizedWO(SpurObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __len__(self):
        return self.number_of_slots


class ClassTable(VariableSizedWO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getitem__(self, index):
        page = index // 1024
        row = index % 1024
        line_address = self.slots[page].cast("Q")[0]
        line = self.memory.object_at(line_address)
        row_address = line.slots[row].cast("Q")[0]
        return self.memory.object_at(row_address)


class VariableSizedW(SpurObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        nb_instvars = self.class_.inst_size


    def __getitem__(self, index):
        if len(self) == 0xFF:
            page = index // 0xFE
            row = index % 0xFE
            line_address = self.array[page]
            line = self.memory[line_address]
            row_address = line.slots[row]
            return self.memory[row_address]

        address = self.array[index]
        return self.memory[address]


class ZeroSized(SpurObject):
    ...

class FixedSized(SpurObject):
    ...

class WeakVariableSized(SpurObject):
    ...

class Indexable(SpurObject):
    indexable64 = 9
    _bytes = [64, 32, 32, 16, 16, 16, 16, 8, 8, 8, 8, 8, 8, 8, 8]
    _shift = [0, 0, 1, 0, 1, 2, 3, 0, 1, 2, 3, 4, 5, 6, 7]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        shift = self.object_format - self.indexable64
        self.nb_bytes = self._bytes[shift]
        self.nb_empty_cases = self._shift[shift]

    def __getitem__(self, index):
        line = index // self.nb_bytes
        row = index % self.nb_bytes
        return self.slots[line][row]

    def __iter__(self):
        return iter((self[i] for i in range(len(self))))

    def __len__(self):
        return self.number_of_slots * self.nb_bytes - self.nb_empty_cases

    def as_text(self):
        return "".join((chr(i) for i in self))

    def __str__(self):
        return f"{super().__str__()}({self.as_text()},)"


class ImmediateInteger(SpurObject):
    class_ = None
    number_of_slots = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update(self, new_address):
        struct.pack("q", new_address)
        self.value = struct.unpack("q", struct.pack("q", new_address))[0] >> 3
        self.class_ = self.memory.smallinteger

    def __getitem__(self, index):
        raise TypeError("ImmediateInteger don't have slots")

    def __repr__(self):
        return f"{super().__repr__()}({self.value})"

    def __eq__(self, other):
        if other.__class__ is not self.__class__:
            return False
        return self.value == other.value

    def __hash__(self):
        return object.__hash__(self)

    def __le__(self, other):
        if other.__class__ is not self.__class__:
            return False
        return self.value <= other.value

    def __lt__(self, other):
        if other.__class__ is not self.__class__:
            return False
        return self.value < other.value

    def __gt__(self, other):
        if other.__class__ is not self.__class__:
            return False
        return self.value > other.value

    def __ge__(self, other):
        if other.__class__ is not self.__class__:
            return False
        return self.value >= other.value

    def __and__(self, other):
        return self.value & other

    def __or__(self, other):
        return self.value | other

    def as_int(self):
        return self.value


spur_implems = {
    0: ZeroSized,
    1: FixedSized,
    2: VariableSizedWO,
    3: VariableSizedW,
    4: WeakVariableSized,
    9: Indexable,
    10: Indexable,
    11: Indexable,
    12: Indexable,
    13: Indexable,
    14: Indexable,
    15: Indexable,
    16: Indexable,
    17: Indexable,
    18: Indexable,
    19: Indexable,
    20: Indexable,
    21: Indexable,
    22: Indexable,
    23: Indexable,
}
SpurObject.spur_implems = spur_implems

i = Image('Pharo8.0.image')
print(i.memory.nil.class_[6])
