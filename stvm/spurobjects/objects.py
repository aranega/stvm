from collections.abc import Sequence


def register_for(o):
    def func(c):
        type_list = o if isinstance(o, tuple) else (o,)
        for t in type_list:
            SpurObject.spur_implems[t] = c
        return c

    return func


class SubList(Sequence):
    def __init__(self, raw_slots, memory):
        self.raw_slots = raw_slots
        self.memory = memory

    def __getitem__(self, i):
        if isinstance(i, slice):
            s = i.start and i.start * 8
            e = i.stop and i.stop * 8
            return self.__class__(self.raw_slots[s:e:i.step], self.memory)
        if i < 0:
            i = len(self) + i
        i = i * 8
        return self.memory.object_at(self.raw_slots[i:i + 8].cast("Q")[0])

    def __len__(self):
        return len(self.raw_slots) // 8


class SpurObject(object):
    spur_implems = {}
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
        self.number_of_slots = nb_slots
        self.raw_object = mem[address:address + self.header_size + (nb_slots * 8)]
        self.header = self.raw_object[:8]
        self.header1 = self.header[:4]
        self.h1 = self.header1.cast("I")[0]
        self.header2 = self.header[4:8]
        self.h2 = self.header2.cast("I")[0]
        self.raw_slots = self.raw_object[8:]
        self.slots = SubList(self.raw_slots, mem)
        self.object_format = (self.h1 & 0x1F000000) >> 24
        self.class_index = self.h1 & 0x3FFFFF
        self.is_immutable = (self.h1 & 0x600000) > 0
        self.is_remembered = (self.h1 & 0x20000000) > 0
        self.is_pinned = (self.h1 & 0x40000000) > 0
        self.identity_hash = self.h2 & 0x3FFFFF

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
        return self.slots[index]

    @property
    def inst_size(self):
        return self[2] & 0xFFFF

    @property
    def class_(self):
        return self.memory.class_table[self.class_index]

    @property
    def name(self):
        try:
            return self[6].as_text()
        except Exception:
            return f"{self[-1][6].as_text()} class"

    def __len__(self):
        return self.number_of_slots


@register_for(0)
class ZeroSized(SpurObject):
    ...


@register_for(1)
class FixedSized(SpurObject):
    ...


@register_for(2)
class VariableSizedWO(SpurObject):
    ...


class ClassTable(VariableSizedWO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.number_of_slots = 1024 * 1024

    def __getitem__(self, index):
        page = index // 1024
        row = index % 1024
        line = self.slots[page]
        return line.slots[row]


@register_for(3)
class VariableSizedW(SpurObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        nb_instvars = self.class_.inst_size
        self.instvars = self.slots[0:nb_instvars]
        self.array = self.slots[nb_instvars:]

    # def instvar(self, index):
    #     return self.memory.object_at(self.instvars[index].cast("Q")[0])
    #
    # def array_at(self, index):
    #     return self.memory.object_at(self.array[index].cast("Q")[0])

@register_for(4)
class WeakVariableSized(SpurObject):
    ...

@register_for(tuple(range(9, 24)))
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
        line = (index // self.nb_bytes) * self.nb_bytes
        row = index % self.nb_bytes
        return self.raw_slots[line + row]

    def __iter__(self):
        return iter(self[i] for i in range(len(self)))

    def __len__(self):
        return len(self.raw_slots) - self.nb_empty_cases

    def as_text(self):
        return "".join(chr(i) for i in self)

    def __repr__(self):
        return f"{super().__repr__()}({self.as_text()})"


@register_for(tuple(range(24, 32)))
class CompiledMethod(SpurObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        method_format = self[0].value
        num_literals = method_format & 0x7FFF
        self.initial_pc = (num_literals + 1) * 8

        self.raw_data = self.raw_object[8:]
        raw = self.raw_data
        pc = self.initial_pc
        if method_format & 0x10000:
            primitive = raw[pc + 1] + (raw[pc + 2] << 8)
        else:
            primitive = 0

        self.sign_flag = method_format < 0
        self.num_literals = num_literals
        self.num_args = (method_format >> 24) & 0x0F
        self.num_temps = (method_format >> 18) & 0x3F
        self.frame_size = 56 if method_format & 0x20000 else 16
        self.primitive = primitive
        self.literals = self.slots[1:num_literals]
        self.bytecodes = raw[num_literals * 8 + 8:-1]
        self.trailer_byte = raw[-1]

    # def literal_at(self, index):
    #     return self.memory.object_at(self.literals[index].cast("Q")[0])

    def size(self):
        return self.number_of_slots * 8 - 8  # - the format header

    @property
    def selector(self):
        return self.literals[len(self.literals) - 1]
