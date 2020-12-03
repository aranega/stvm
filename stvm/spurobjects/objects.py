from collections.abc import Sequence
import struct


def spurobject(o):
    def func(c):
        type_list = o if isinstance(o, range) else (o,)
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

    def __setitem__(self, i, val):
        if isinstance(i, slice):
            raise TypeError("Slice over sublist is not yet impl")
        if i < 0:
            i = len(self) + i
        i = i * 8
        if isinstance(val, SpurObject):
            self.raw_slots[i:i + 8] = struct.pack("Q", val.address)
        else:
            raise TypeError("Non spur object in slot like?", val)

    def __len__(self):
        return len(self.raw_slots) // 8


class SpurObject(object):
    spur_implems = {}
    special_subclasses = {}
    header_size = 8

    def __init__(self, address, memory, kind=None):
        self.memory = memory
        self._address = address
        self.update(address)
        self.kind = kind

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
        _, nb_slots, cls_index = self.decode_basicinfo(header)
        if nb_slots > 254:
            nb_slots = mem[address - 8 : address - 4].cast("I")[0]
        self.number_of_slots = nb_slots
        self.class_index = cls_index
        self.raw_object = mem[address:address + self.header_size + (nb_slots * 8)]
        self.header = self.raw_object[:8]
        self.header1 = self.header[:4]
        self.h1 = self.header1.cast("I")[0]
        self.header2 = self.header[4:8]
        self.h2 = self.header2.cast("I")[0]
        self.raw_slots = self.raw_object[8:]
        self.slots = SubList(self.raw_slots, mem)
        self.object_format = (self.h1 & 0x1F000000) >> 24
        self.is_immutable = (self.h1 & 0x600000) > 0
        self.is_remembered = (self.h1 & 0x20000000) > 0
        self.is_pinned = (self.h1 & 0x40000000) > 0
        self.identity_hash = self.h2 & 0x3FFFFF

    @classmethod
    def find_spurClass(cls, obj_format, cls_index):
        return cls.special_subclasses.get((obj_format, cls_index), cls.spur_implems[obj_format])


    @classmethod
    def create(cls, address, memory, class_table=False):
        header = memory[address:address + 8]
        obj_format, _, cls_index = cls.decode_basicinfo(header)
        SpurClass = ClassTable if class_table else cls.find_spurClass(obj_format, cls_index)
        obj = SpurClass(address, memory, obj_format)
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
        _, nb_slots, _ = self.decode_basicinfo(header)
        if nb_slots == 0xFF:
            return self.memory.object_at(new_object_address)
        return self.memory.object_at(self.end_address)

    @staticmethod
    def decode_basicinfo(header):
        f, g = header.cast("I")
        number_of_slots = (g & 0xFF000000) >> 24
        object_format = (f & 0x1F000000) >> 24
        class_index = f & 0x3FFFFF
        return (object_format, number_of_slots, class_index)

    def __getitem__(self, index):
        return self.slots[index]

    def __setitem__(self, index, value):
        self.slots[index] = value

    @property
    def inst_size(self):
        return self[2] & 0xFFFF

    @property
    def inst_format(self):
        return (self[2].value & 0xFFFF0000) >> 16

    @property
    def class_(self):
        return self.memory.class_table[self.class_index]

    @property
    def name(self):
        try:
            return self[6].as_text()
        except Exception:
            return f"{self[-1][6].as_text()} class"

    def display(self):
        if self is self.memory.nil:
            return "nil"
        if self is self.memory.true:
            return "true"
        if self is self.memory.false:
            return "false"
        return f"<0x{self.address:x} of {self.class_.name}>"

    def __len__(self):
        return self.number_of_slots


@spurobject(0)
class ZeroSized(SpurObject):
    ...


@spurobject(1)
class FixedSized(SpurObject):
    ...


@spurobject(2)
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


@spurobject(3)
class VariableSizedW(SpurObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        nb_instvars = self.class_.inst_size
        self.instvars = self.slots[:nb_instvars]
        self.array = self.slots[nb_instvars:]


@spurobject(4)
class WeakVariableSized(SpurObject):
    ...


@spurobject(range(9, 24))
class Indexable(SpurObject):
    indexable64 = 9
    _bits = [64, 32, 32, 16, 16, 16, 16, 8, 8, 8, 8, 8, 8, 8, 8]
    _shift = [0, 0, 1, 0, 1, 2, 3, 0, 1, 2, 3, 4, 5, 6, 7]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        shift = self.object_format - self.indexable64
        self.nb_bits = self._bits[shift]
        self.nb_empty_cases = self._shift[shift]

    def raw_at(self, index):
        nbbits = self.nb_bits
        line = (index // nbbits) * nbbits
        offset = 8 // (64 // nbbits)
        row = (index % nbbits) * offset
        return int.from_bytes(self.raw_slots[line + row: line + row + offset], byteorder="little")


    def __getitem__(self, index):
        return integer.create(self.raw_at(index), self.memory)

    def __iter__(self):
        return (self[i] for i in range(len(self)))

    def __len__(self):
        nbbytes = len(self.raw_slots) - self.nb_empty_cases
        return nbbytes * 8 // self.nb_bits

    def as_text(self):
        # return "".join(chr(i) for i in self)
        raw_at = self.raw_at
        return "".join(chr(raw_at(i)) for i in range(len(self)))

    def as_int(self):
        result = 0
        for i in reversed(self):
            result = (result << self.nb_bits) + i.value
        return result

    def __int__(self):
        return self.as_int()

    def as_float(self):
        val = self.raw_at(0) << self.nb_bits | self.raw_at(1)
        val = struct.unpack(">d", struct.pack(">Q", val))[0]
        return val

    def __repr__(self):
        return f"{super().__repr__()}({self.as_text()})"


@spurobject(range(24, 32))
class CompiledMethod(SpurObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        method_format = super().__getitem__(0).value
        num_literals = method_format & 0x7FFF
        self.initial_pc = (num_literals + 1) * 8

        self.raw_data = self.raw_object[8:8 + self.size()]
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
        # self.trailer_byte = raw[-1]
        self.trailer = MethodTrailer(raw[-1], self)
        self.bytecodes = raw[num_literals * 8 + 8:-self.trailer.size]

    def __getitem__(self, i):
        if not isinstance(i, slice) and i > self.initial_pc:
            return integer.create(self.raw_data[i], self.memory)
        return super().__getitem__(i)

    def size(self):
        return self.number_of_slots * 8 - (self.kind - 24)

    @property
    def selector(self):
        selector = self.literals[-1]
        if selector.kind == 3:
            selector = selector[1]
        return selector


class MethodTrailer(object):
    def __init__(self, trailer_byte, compiled_method):
        self.compiled_method = compiled_method
        self.trailer_byte = trailer_byte
        self.decode()

    def decode_length(self):
        num_bytes = self.trailer_byte & 0x03
        raw = self.compiled_method.raw_data
        length = int.from_bytes(self.compiled_method.raw_data[-num_bytes-1:], byteorder="little")
        self.size = length + num_bytes
        return length

    def decode_notrailer(self):
        self.size = 4

    def decode_sourcepointer(self):
        self.size = 4

    def decode_varlengthsourcepointer(self):
        cm = self.compiled_method
        method_size = cm.size()
        pos = method_size - 2
        shift = data = 0
        while "Value smaller than 127":
            value = cm.raw_data[pos]
            data = ((value & 0x7F) << shift) + data
            pos -= 1
            shift += 7
            if value <= 127:
                break

        self.size = method_size - pos - 1

    def decode(self):
        self.data = None
        self.size = None
        flag_byte = self.trailer_byte
        kind = flag_byte >> 2
        if kind == 0b000000:
            self.size = 1
        elif kind == 0b000001:
            self.decode_length()
        elif kind == 0b000010:
            self.decode_length()
        elif kind == 0b000011:
            self.decode_length()
        elif kind == 0b000100:
            self.size = 1
        elif kind == 0b000101:
            self.decode_length()
        elif kind == 0b000110:
            self.decode_length()
        elif kind == 0b000111:
            self.decode_length()
        elif kind == 0b000111:
            self.decode_length()
        elif kind == 0b001000:
            self.decode_varlengthsourcepointer()
        elif kind == 0b001001:
            self.size = 2
        elif kind == 0b111111:
            self.size = 4
        else:
            import ipdb; ipdb.set_trace()


from .immediate import ImmediateInteger as integer
