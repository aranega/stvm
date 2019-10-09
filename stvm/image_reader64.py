import struct
from collections import namedtuple
from collections.abc import Sequence
from enum import Enum, unique
from functools import lru_cache, wraps
import itertools


object_types = {}


class ObjectHeader(object):
    def __init__(self, class_index, is_immutable, remaining_bits_3, object_format, is_pinned, is_grey, is_remembered, identity_hash, is_marked, remaining_bits, number_of_slots):
        self.class_index = class_index
        self.is_immutable = is_immutable
        self.remaining_bits_3 = remaining_bits_3
        self.object_format = object_format
        self.is_pinned = is_pinned
        self.is_grey = is_grey
        self.is_remembered = is_remembered
        self.identity_hash = identity_hash
        self.is_marked = is_marked
        self.remaining_bits = remaining_bits
        self.number_of_slots = number_of_slots

    def encode(self):
        f = self.class_index
        f |= 0x400000 if self.remaining_bits_3 else 0
        f |= 0x600000 if self.is_immutable else 0
        f |= self.object_format << 24
        f |= 0x20000000 if self.is_remembered else 0
        f |= 0x40000000 if self.is_pinned else 0
        f |= 0x60000000 if self.is_grey else 0

        g = self.identity_hash & 0x3FFFFF
        g |= 0x400000 if self.remaining_bits else 0
        g |= 0x600000 if self.is_marked else 0
        g |= self.number_of_slots << 24
        return (f, g)

    def __repr__(self):
        return f"{self.__class__.__name__}{vars(self)}"


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
    SMALLINT_2 = 3
    SMALLFLOAT = 4


class SpurObject(Sequence):
    @staticmethod
    def create(address, from_cls, memory, array_size=0):
        if isinstance(array_size, ImmediateInteger):
            array_size = array_size.value

        nb_slots = from_cls.inst_size + array_size
        object_format = from_cls.inst_format
        if ObjectFormat.INDEXABLE_64.value <= object_format <= ObjectFormat.INDEXABLE_8_8.value:
            shift = object_format - ObjectFormat.INDEXABLE_64.value
            ibs = IndexableObject._item_by_slot[shift]
            size = nb_slots // ibs
            extra_cases = nb_slots % ibs
            extra_slot = 1 if extra_cases > 0 else 0
            object_format = object_format + (ibs - extra_cases) * extra_slot
            nb_slots = size + extra_slot

        if nb_slots > 254:
            memory[address: address + 8] = struct.pack('Q', nb_slots)
            address = address + 8  # We shift from 64 bits
            nb_slots = 255

        header = ObjectHeader(
            class_index=from_cls.header.identity_hash,
            is_immutable=from_cls.header.is_immutable,
            remaining_bits_3=False,
            object_format=object_format,
            is_pinned=False,
            is_grey=False,
            is_remembered=False,
            identity_hash=None,
            is_marked=False,
            remaining_bits=False,
            number_of_slots=nb_slots,
        )
        header.identity_hash = id(header)
        encoded_header = header.encode()
        memory[address: address + 8] = struct.pack('II', *encoded_header)
        instance = object_types[object_format](header, address, memory)
        if not isinstance(instance, IndexableObject):
            for i in range(len(instance)):
                instance.wslots[i] = memory.nil
        return instance


    def __init__(self, header, address, memory, nb_slots=None):
        self.header = header
        self.object_format = ObjectFormat(header.object_format)
        self.address = address
        self.memory = memory

        start_slots = address + 8
        end_slots = self.nb_slots * 8
        slots = memory.raw[start_slots:start_slots + end_slots]
        self.raw = slots
        self.slots = [slots[i : i + 8] for i in range(0, len(slots), 8)]
        self.wslots = MemoryFragment(self.slots[:], self.memory)
        self.instvars = self.wslots
        self.array = MemoryFragment([], self.memory)

    @property
    def _end_address_nbslots(self):
        adr = self.address
        raw = self.memory.raw
        n = self.header.number_of_slots
        nb_slots = n if n < 255 else int.from_bytes(raw[adr - 8 : adr], "little")
        slots_size = max(nb_slots, 1) * 8
        header_size = 8
        basic_size = header_size + slots_size
        padding = basic_size % 8
        return self.address + basic_size + padding, nb_slots

    @property
    def nb_slots(self):
        _, nbslots = self._end_address_nbslots
        return nbslots

    @property
    def end_address(self):
        end, _ = self._end_address_nbslots
        return end

    @property
    def inst_size(self):
        return self[2].value & 0xFFFF

    @property
    def inst_format(self):
        return (self[2].value & 0xFFFF0000) >> 16

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
        return self.memory[bytes(address)]

    def __iter__(self):
        return iter((self[i] for i in range(len(self))))

    def __len__(self):
        return len(self.slots)

    def __hash__(self):
        return object.__hash__(self)

    def __eq__(self, other):
        if other.__class__ is not self.__class__:
            return False

        h1 = self.header
        h2 = other.header
        if (h1.class_index != h2.class_index
            or h1.object_format != h2.object_format
            or h1.number_of_slots != h2.number_of_slots):
            return False

        for x, y in zip(self, other):
            if x != y:
                break
        else:
            return True

        return False


def create_instance(address, for_cls, memory, array_size=0):
    return for_cls.__class__.create(address, for_cls, memory, array_size=array_size)


def register_for(o):
    def func(c):
        type_list = o if isinstance(o, tuple) else (o,)
        for t in type_list:
            object_types[t.value] = c
        return c

    return func


@register_for(ObjectFormat.VARIABLE_SIZED_WO)
class VariableSizedWO(SpurObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.array, self.instvars = self.instvars, self.array


class ClassTable(VariableSizedWO):
    def __init__(self, header, address, memory):
        super().__init__(header, address, memory)

    def __getitem__(self, index):
        if isinstance(index, str):
            return self.search_class(index)
        page = index // 1024
        row = index % 1024
        line = self.memory[bytes(self.slots[page])]
        row_address = line.slots[row]
        return self.memory[bytes(row_address)]

    def search_class(self, name):
        for c in self:
            if c is self.memory.nil:
                continue
            if c.header.number_of_slots > 6 and c[6].as_text() == name:
                return c


@register_for(ObjectFormat.VARIABLE_SIZED_W)
class VariableSizedW(SpurObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        nb_instvars = self.class_.inst_size
        self.array.slots = self.slots[nb_instvars:]
        self.instvars.slots = self.slots[:nb_instvars]


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
    _shift = [0, 0, 1, 0, 1, 2, 3, 0, 1, 2, 3, 4, 5, 6, 7]
    _item_by_slot = [1, 2, 2, 4, 4, 4, 4, 8, 8, 8, 8, 8, 8, 8, 8]  # 32b dependent

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        shift = self.header.object_format - ObjectFormat.INDEXABLE_64.value
        self.item_by_slot = self._item_by_slot[shift]
        self.nb_empty_cases = self._shift[shift]
        self.item_length = 8 // self.item_by_slot
        self.array = self

    def __getitem__(self, index):
        line = index // self.item_by_slot
        col = index % self.item_by_slot
        return self.slots[line][col : col + self.item_length]

    def __setitem__(self, index, item):
        line = index // self.item_by_slot
        col = index % self.item_by_slot
        data = int.to_bytes(item, length=self.item_length, byteorder='little')
        self.slots[line][col : col + self.item_length] = data
        # struct.pack_into("I", self.slots[line][row], 0, data)

    def __iter__(self):
        return iter((self[i] for i in range(len(self))))

    def __len__(self):
        if self.header.number_of_slots == 0:
            return 0
        return self.header.number_of_slots * self.item_by_slot - self.nb_empty_cases

    def as_text(self):
        return "".join((chr(i[0]) for i in self))

    def as_int(self):
        result = b''
        for i in self:
            tmp = i[0:self.item_length].tobytes()
            result = result + tmp
        return int.from_bytes(result, byteorder='little')



@register_for(ObjectFormat.FIXED_SIZED)
class FixedSized(SpurObject):
    pass


@register_for(ObjectFormat.ZERO_SIZED)
class ZeroSized(SpurObject):
    pass


CompiledMethodHeader = namedtuple(
    "CompiledMethodHeader",
    "sign_flag num_literals num_args num_temps frame_size primitive",
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
        method_format = int.from_bytes(self.slots[0], "little") >> 1
        num_literals = method_format & 0x7FFF
        self.initial_pc = (num_literals + 1) * 8

        if method_format & 0x10000:
            primitive = self.raw[self.initial_pc + 1] + (
                self.raw[self.initial_pc + 2] << 8
            )
        else:
            primitive = 0
        self.raw = self.raw[4:]

        self.method_header = CompiledMethodHeader(
            sign_flag=method_format < 0,
            num_literals=num_literals,
            num_args=(method_format >> 24) & 0x0F,
            num_temps=(method_format >> 18) & 0x3F,
            frame_size=56 if method_format & 0x20000 else 16,
            primitive=primitive,
        )

    @property
    def bytecode(self):
        return self.raw[self.method_header.num_literals * 8:]

    @property
    def literals(self):
        return MemoryFragment(
            self.slots[1 : self.method_header.num_literals + 1], self.memory
        )

    def size(self):
        return len(self.slots) * 4 - 4  # - the format header

    @property
    def selector(self):
        return self.literals[0]

    @property
    def selector_name(self):
        return self.selector.as_text()

    def extract_block(self, copied, num_args, from_, block_size, outer_context):
        return BlockClosure(copied, num_args, from_, block_size, outer_context, self)


class BlockClosure(object):
    def __init__(self, copied, num_args, from_, block_size, outer_context, compiled_method):
        self.copied = copied
        self.num_args = num_args
        self.block_size = block_size
        self.outer_context = outer_context
        self.compiled_method = compiled_method
        self.from_ = from_
        self.home_context = None

    @property
    def literals(self):
        return self.compiled_method.literals

    @property
    def bytecode(self):
        cm = self.compiled_method
        return cm.bytecode[self.from_ : self.from_ + self.block_size]

    @property
    def method_header(self):
        return self

    @property
    def memory(self):
        return self.compiled_method.memory

    @property
    def num_temps(self):
        return self.compiled_method.method_header.num_temps + len(self.copied)

    @property
    @lru_cache(1)
    def class_(self):
        # return self.compiled_method.memory.classes_table.search_class('BlockClosure')
        return self.compiled_method.memory.special_object_array[36]

    def extract_block(self, copied, num_args, from_, block_size, outer_context):
        return BlockClosure(copied, num_args, from_, block_size, outer_context, self)


class ImmediateInteger(object):
    def __init__(self, raw=None, memory=None):
        if raw:
            self.address = int.from_bytes(raw, "little")
            self.value = struct.unpack("q", raw)[0] >> 3
        if memory:
            self.class_ = memory.smallinteger

    # @property
    # def instvars(self):
    #     return [self] * (self.class_.inst_size + 2)

    def __getitem__(self, index):
        return self

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

    def as_int(self):
        return self.value


def build_int(value, memory):
    immediate = ImmediateInteger(memory=memory)
    assert -2147483648 <= value < 2147483648  # 32b dependent
    immediate.value = value
    value <<= 3
    value &= 0xFFFFFFFFFFFFFFFF
    value |= 0x001
    immediate.address = value
    return immediate


def build_char(value, memory):
    immediate = ImmediateChar(memory=memory)
    immediate.value = chr(value)
    value <<= 3
    value &= 0xFFFFFFFFFFFFFFFF
    value |= 0x010
    immediate.address = value
    return immediate


class ImmediateChar(object):
    def __init__(self, raw=None, memory=None):
        if raw:
            self.address = int.from_bytes(raw, "little")
            self.value = chr(self.address >> 3 & 0xFFFFFFFFFFFFFFFF)
        if memory:
            self.memory = memory
            self.class_ = memory.character

    def __getitem__(self, index):
        return self

    def __repr__(self):
        return f"{super().__repr__()}({self.value})"

    def __eq__(self, other):
        if other.__class__ is not self.__class__:
            return False
        return self.value == other.value

    def __hash__(self):
        return object.__hash__(self)


class MemoryFragment(Sequence):
    def __init__(self, slots, memory):
        self.slots = slots
        self.memory = memory

    def __getitem__(self, index):
        address = self.slots[index]
        return self.memory[bytes(address)]

    def __setitem__(self, i, item):
        if isinstance(i, slice):
            raise NotImplementedError()
        if isinstance(item, ImmediateInteger):
            # struct.pack_into("I", self.slots[i], 0, (item.value << 1) | 0x1)
            struct.pack_into("Q", self.slots[i], 0, item.address)
            return
        if isinstance(item, ImmediateChar):
            struct.pack_into("Q", self.slots[i], 0, item.address)
            return
        struct.pack_into("Q", self.slots[i], 0, item.address)


    def __iter__(self):
        return iter((self[i] for i in range(len(self))))

    def __len__(self):
        return len(self.slots)


class Memory(object):
    class InnerMemory(object):
        def __init__(self, image_header, raw):
            self.raw_image = raw
            self.raw_young = memoryview(bytearray(b'\x00') * image_header.old_base_address)
            self.image_header = image_header
            self.old_base_address = self.image_header.old_base_address

        def __getitem__(self, i):
            offset = self.old_base_address
            if isinstance(i, slice):
                if i.start < self.old_base_address:
                    return self.raw_young[i.start : i.stop : i.step]
                return self.raw_image[i.start - offset : i.stop - offset : i.step]
            if i < self.old_base_address:
                return self.raw_young[i]
            return self.raw_image[i - offset]

        def __setitem__(self, i, item):
            if isinstance(i, slice):
                if i.start < self.old_base_address:
                    self.raw_young[i] = item
                    return
                self.raw_image[i.start - offset : i.stop - offset : i.step] = item
                return
            if i < self.old_base_address:
                self.raw_young[i] = item
                return
            self.raw_image[i - offset] = item

        def __iter__(self):
            return itertools.chain(iter(self.raw_young), iter(self.raw_image))

        def __len__(self):
            return len(self.raw_image) + len(self.raw_young)


    def __init__(self, image_header, raw):
        self.raw = Memory.InnerMemory(image_header, raw)
        self.image_header = image_header

    def address_points_to(self, address):
        return AddressType(address & 0x03)

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
        if isinstance(address, (bytes, bytearray)):
            address = int.from_bytes(address, "little")

        if self.address_points_to(address) in (AddressType.SMALLINT, AddressType.SMALLINT_2):
            return ImmediateInteger(raw, self)
        if self.address_points_to(address) is AddressType.CHAR:
            return ImmediateChar(raw, self)

        header = self._decode_header(address)
        if class_table:
            return ClassTable(header, address, self)
        clazz = object_types.get(header.object_format, SpurObject)
        return clazz(header, address, self)

    def __setitem__(self, i, item):
        self.raw.__setitem__(i, item)

    @property
    def nil(self):
        return self.special_object_array[0]

    @property
    def false(self):
        return self.special_object_array[1]

    @property
    def true(self):
        return self.special_object_array[2]

    @property
    def free_list(self):
        return self.true.next_object

    @property
    @lru_cache(1)
    def bytestring(self):
        return self.special_object_array[6]

    @property
    @lru_cache(1)
    def smallinteger(self):
        return self.special_object_array[5]

    @property
    @lru_cache(1)
    def context_class(self):
        return self.special_object_array[10]

    @property
    @lru_cache(1)
    def largepositiveint(self):
        return self.special_object_array[13]

    @property
    @lru_cache(1)
    def character(self):
        return self.special_object_array[19]

    @property
    @lru_cache(1)
    def array(self):
        return self.special_object_array[7]
        # try:
        #     assert e[6].as_text() == 'Array'
        #     return e
        # except Exception:
        #     for e in self.classes_table:
        #         if e is self.nil:
        #             continue
        #         try:
        #             if e[6].as_text() == 'Array':
        #                 return e
        #         except Exception:
        #             pass
        #     raise Exception("No array in your image!")

    @property
    @lru_cache()
    def classes_table(self):
        extended_header_size = 8
        return self.__getitem__(
            self.true.next_object.end_address + extended_header_size, class_table=True
        )

    @property
    def special_object_array(self):
        return self[self.image_header.special_object_oop]


ImageHeader = namedtuple(
    "ImageHeader",
    "image_version header_size data_size old_base_address special_object_oop last_hash saved_window_size header_flags",
)


class Image(object):
    # header_format = "IIIIIIII"
    header_format = "IIQQQQQI"

    def __init__(self, raw):
        self.raw = memoryview(raw)
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
