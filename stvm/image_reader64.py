
import struct
from collections import namedtuple
from collections.abc import Sequence
from enum import Enum, unique
from functools import lru_cache, wraps


ImageHeader = namedtuple(
    "ImageHeader",
    "image_version header_size data_size old_base_address special_object_oop last_hash saved_window_size header_flags extra_VM_memory hdr_num_stack_pages hdr_eden_bytes hdr_max_ext_sem_tab_size second_unknown_short first_seg_size",
)
ObjectHeader = namedtuple(
    "ObjectHeader",
    "class_index is_immutable remaining_bits_3 object_format is_pinned is_grey is_remembered identity_hash is_marked remaining_bits number_of_slots",
)


@unique
class ObjectFormat(Enum):
    ZERO_SIZED = 0
    FIXED_SIZED = 1
    VARIABLE_SIZED_WO = 2
    VARIABLE_SIZED_W = 3
    WEAK_VARIABLE_SIZED = 4
    WEAK_FIXED_SIZED = 5
    UNUSED_6 = 6
    UNUSED_7 = 7
    UNUSED_8 = 8
    INDEXABLE_64 = 9
    INDEXABLE_32 = 10
    INDEXABLE_32_2 = 11
    INDEXABLE_16 = 12
    INDEXABLE_16_2 = 13
    INDEXABLE_16_3 = 14
    INDEXABLE_16_4 = 15
    INDEXABLE_8 = 16
    INDEXABLE_8_2 = 17
    INDEXABLE_8_3 = 18
    INDEXABLE_8_4 = 19
    INDEXABLE_8_5 = 20
    INDEXABLE_8_6 = 21
    INDEXABLE_8_7 = 22
    INDEXABLE_8_8 = 23
    COMPILED_METHOD = 24
    COMPILED_METHOD_2 = 25
    COMPILED_METHOD_3 = 26
    COMPILED_METHOD_4 = 27
    COMPILED_METHOD_5 = 28
    COMPILED_METHOD_6 = 29
    COMPILED_METHOD_7 = 30
    COMPILED_METHOD_8 = 31


@unique
class AddressType(Enum):
    OBJECT = 0
    SMALLINT = 1
    CHAR = 2
    SMALLFLOAT = 3


class SpurObject(Sequence):
    def __init__(self, header, address, memory):
        self.header = header
        self.object_format = ObjectFormat(header.object_format)
        self.address = address
        self.memory = memory

        start_slots = address + 8
        end_slots = start_slots + (header.number_of_slots * 8)
        slots = memory.raw[start_slots:end_slots]
        self.raw = slots
        self.slots = [slots[i : i + 8] for i in range(0, len(slots), 8)]
        self.instvars = MemoryFragment(self.slots[:], self.memory)
        self.array = MemoryFragment([], self.memory)

    @property
    def end_address(self):
        header_size = 8
        slots_size = max(len(self.slots), 1) * 8
        basic_size = header_size + slots_size
        padding = basic_size % 8
        return self.address + basic_size + padding

    @property
    def inst_size(self):
        return self[2].value & 0xFFFF

    @property
    def extra_headers(self):
        if len(self) < 0xFF:
            return tuple()
        headers = []
        address = self.address
        header = self.memory._decode_header(address)
        while header.number_of_slots == 0xFF:
            address = address - 8
            header = self.memory._decode_header(address)
            headers.append(header)
        return headers

    @property
    def next_object(self):
        new_object_address = self.end_address + 8
        new_object_header = self.memory._decode_header(new_object_address)
        if new_object_header.number_of_slots == 0xFF:
            return self.memory[new_object_address]
        return self.memory[self.end_address]

    @property
    def class_(self):
        return self.memory.classes_table[self.header.class_index]

    def __getitem__(self, index):
        address = self.slots[index]
        return self.memory[address]

    def __iter__(self):
        return iter((self[i] for i in range(len(self))))

    def __len__(self):
        return len(self.slots)


object_types = {}


def register_for(o):
    def func(c):
        type_list = o if isinstance(o, tuple) else (o,)
        for t in type_list:
            object_types[t.value] = c
        return c

    return func


class MemoryFragment(object):
    def __init__(self, slots, memory):
        self.slots = slots
        self.memory = memory

    def __getitem__(self, index):
        address = self.slots[index]
        return self.memory[address]

    def __iter__(self):
        return iter((self[i] for i in range(len(self))))

    def __len__(self):
        return len(self.slots)


@register_for(ObjectFormat.VARIABLE_SIZED_WO)
class VariableSizedWO(SpurObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.array, self.instvars = self.instvars, self.array

    def __getitem__(self, index):
        if len(self) == 0xFF:
            page = index // 0xFF
            row = index % 0xFF
            line_address = self.slots[page]
            line = self.memory[line_address]
            row_address = line.slots[row]
            return self.memory[row_address]

        address = self.slots[index]
        return self.memory[address]


class ClassTable(VariableSizedWO):
    def __init__(self, header, address, memory):
        self.header = header
        self.object_format = ObjectFormat(header.object_format)
        self.address = address
        self.memory = memory

        start_slots = address + 8
        end_slots = start_slots + (4096 * 8)
        slots = memory.raw[start_slots:end_slots]
        self.slots = [slots[i : i + 8] for i in range(0, len(slots), 8)]
        self.array = MemoryFragment(self.slots[:], self.memory)
        self.instvars = MemoryFragment([], self.memory)

    def __getitem__(self, index):
        page = index // 1024
        row = index % 1024
        line_address = self.slots[page]
        line = self.memory[line_address]
        row_address = line.slots[row]
        return self.memory[row_address]


@register_for(ObjectFormat.VARIABLE_SIZED_W)
class VariableSizedW(SpurObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        nb_instvars = self.class_.inst_size
        self.array.slots = self.slots[nb_instvars:]
        self.instvars.slots = self.slots[:nb_instvars]

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



@register_for(ObjectFormat.WEAK_VARIABLE_SIZED)
class WeakVariableSized(SpurObject):
    pass


@register_for(ObjectFormat.WEAK_FIXED_SIZED)
class WeakFixedSized(SpurObject):
    pass


@register_for(
    (
        ObjectFormat.INDEXABLE_64,
        ObjectFormat.INDEXABLE_32,
        ObjectFormat.INDEXABLE_32_2,
        ObjectFormat.INDEXABLE_16,
        ObjectFormat.INDEXABLE_16_2,
        ObjectFormat.INDEXABLE_16_3,
        ObjectFormat.INDEXABLE_16_4,
        ObjectFormat.INDEXABLE_8,
        ObjectFormat.INDEXABLE_8_2,
        ObjectFormat.INDEXABLE_8_3,
        ObjectFormat.INDEXABLE_8_4,
        ObjectFormat.INDEXABLE_8_5,
        ObjectFormat.INDEXABLE_8_6,
        ObjectFormat.INDEXABLE_8_7,
        ObjectFormat.INDEXABLE_8_8,
    )
)
class IndexableObject(SpurObject):
    _bytes = [64, 32, 32, 16, 16, 16, 16, 8, 8, 8, 8, 8, 8, 8, 8]
    _shift = [0, 0, 1, 0, 1, 2, 3, 0, 1, 2, 3, 4, 5, 6, 7]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        shift = self.header.object_format - ObjectFormat.INDEXABLE_64.value
        self.nb_bytes = self._bytes[shift]
        self.nb_empty_cases = self._shift[shift]

    def __getitem__(self, index):
        line = index // self.nb_bytes
        row = index % self.nb_bytes
        return self.slots[line][row]

    def __iter__(self):
        return iter((self[i] for i in range(len(self))))

    def __len__(self):
        return super().__len__() * self.nb_bytes - self.nb_empty_cases


@register_for(ObjectFormat.FIXED_SIZED)
class FixedSized(SpurObject):
    pass


@register_for(ObjectFormat.ZERO_SIZED)
class ZeroSized(SpurObject):
    pass


CompiledMethodHeader = namedtuple(
    "CompiledMethodHeader",
    "sign_flag num_literals num_args num_temps frame_size primitive"
)

@register_for(
    (
        ObjectFormat.COMPILED_METHOD,
        ObjectFormat.COMPILED_METHOD_2,
        ObjectFormat.COMPILED_METHOD_3,
        ObjectFormat.COMPILED_METHOD_4,
        ObjectFormat.COMPILED_METHOD_5,
        ObjectFormat.COMPILED_METHOD_6,
        ObjectFormat.COMPILED_METHOD_7,
        ObjectFormat.COMPILED_METHOD_8,
    )
)
class CompiledMethod(SpurObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        method_format = self.instvars[0].value
        num_literals = method_format & 0x7FFF
        self.initial_pc = (num_literals + 1) * 8

        self.raw = self.raw[4:]
        if method_format & 0x10000:
            primitive = self.raw[self.initial_pc + 1] + (self.raw[self.initial_pc + 2] << 8)
        else:
            primitive = 0

        self.method_header = CompiledMethodHeader(
            sign_flag=method_format < 0,
            num_literals=num_literals,
            num_args=(method_format >> 24) & 0x0F,
            num_temps=(method_format >> 18) & 0x3F,
            frame_size=56 if method_format & 0x20000 else 16,
            primitive = primitive,
        )

    @property
    def bytecode(self):
        return self.slots[self.method_header.num_literals + 1:]

    def size(self):
        return len(self.slots) * 8 - 4  # - the format header



class ImmediatInteger(object):
    def __init__(self, raw):
        self.address = int.from_bytes(raw, "little")
        self.value = struct.unpack("q", raw)[0] >> 3

    def __repr__(self):
        return f"{super().__repr__()}({self.value})"


class ImmediatChar(object):
    def __init__(self, address):
        self.address = int.from_bytes(raw, "little")
        self.value = chr(struct.unpack("2s", raw)[0] >> 3)

    def __repr__(self):
        return f"{super().__repr__()}({self.value})"


class Memory(object):
    class InnerMemory(object):
        def __init__(self, image_header, raw):
            self.raw = raw
            self.image_header = image_header
            self.old_base_address = self.image_header.old_base_address

        def __getitem__(self, i):
            offset = self.old_base_address
            if isinstance(i, slice):
                return self.raw[i.start - offset : i.stop - offset : i.step]
            return self.raw[i - offset]

        def __len__(self):
            return len(self.raw)

        def __iter__(self):
            return iter(self.raw)

    def __init__(self, image_header, raw):
        self.raw = Memory.InnerMemory(image_header, raw)
        self.image_header = image_header

    def address_points_to(self, address):
        return AddressType(address & 0x07)

    def _decode_header(self, address):
        f, g = self.raw[address : address + 4], self.raw[address + 4 : address + 8]
        f, g = int.from_bytes(f, "little"), int.from_bytes(g, "little")
        header = ObjectHeader(
            class_index=f & 0x3FFFFF,
            remaining_bits_3=(f & 0x400000) > 0,
            is_immutable=(f & 0x600000) > 0,
            object_format=(f & 0x1F000000) >> 24,
            is_remembered=(f & 0x20000000) > 0,
            is_pinned=(f & 0x40000000) > 0,
            is_grey=(f & 0x60000000) > 0,
            identity_hash=g & 0x3FFFFF,
            remaining_bits=(g & 0x400000) > 0,
            is_marked=(g & 0x600000) > 0,
            number_of_slots=(g & 0xFF000000) >> 24,
        )
        return header

    @lru_cache()
    def __getitem__(self, address, class_table=False):
        raw = address
        if isinstance(address, bytes):
            address = int.from_bytes(address, "little")

        if self.address_points_to(address) is AddressType.SMALLINT:
            return ImmediatInteger(raw)
        if self.address_points_to(address) is AddressType.CHAR:
            return ImmediatChar(raw)

        header = self._decode_header(address)
        if class_table:
            return ClassTable(header, address, self)
        clazz = object_types.get(header.object_format, SpurObject)
        return clazz(header, address, self)

    @property
    def nil(self):
        return self.special_object_array[0]

    @property
    def false(self):
        a = self.special_object_array[1]
        print(a.address)
        return a

    @property
    def true(self):
        a = self.special_object_array[2]
        print(a.address)
        return a

    @property
    @lru_cache()
    def classes_table(self):
        extended_header_size = 8
        print("sqd", self.true.next_object.address)
        return self.__getitem__(self.true.next_object.end_address + extended_header_size, class_table=True)

    @property
    def special_object_array(self):
        return self[self.image_header.special_object_oop]


class Image(object):
    header_format = "IILLLLLLIHIHHL"

    def __init__(self, raw):
        self.raw = raw
        header_size = struct.calcsize(self.header_format)
        self.header = ImageHeader._make(
            struct.unpack(self.header_format, raw[:header_size])
        )

    @property
    def raw_mem(self):
        return self.raw[self.header.header_size :]

    @property
    def raw_header(self):
        return self.raw[: self.header.header_size]

    @property
    def mem(self):
        return Memory(self.header, self.raw_mem)


class VM(object):
    def __init__(self):
        self.mem = None
        self.image = None

    def open_image(
        self, image_file="Pharo8.0.image"
    ):
        with open(image_file, "rb") as f:
            self.image = Image(f.read())
            self.mem = self.image.mem


vm = VM()
vm.open_image()
vm.mem.classes_table
#
#
# def scan(mem, size=10):
#     current = mem.nil
#     i = 0
#     while current.next_object is not None:
#         if size > 1 and i >= size:
#             return i
#         print(current.header)
#         current = current.next_object
#         i += 1
#
#     return i
#
#
# integer_dict = vm.mem.classes_table[1][0][1]
