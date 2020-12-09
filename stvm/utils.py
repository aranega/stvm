import struct
from math import ceil
from .spurobjects import ImmediateInteger as integer
from .spurobjects import ImmediateFloat as smallfloat

LargeNegativeIntClass = 32
LargePositiveIntClass = 33
SMALLINT_MAX = 1152921504606846975
SMALLINT_MIN = -1152921504606846976


# def build_largepositiveint(value, vm):
#     cls = vm.memory.largepositiveint
#     size = (value.bit_length() + 7) // 8
#     array_size = (size//(8 + 1)) + 1
#     inst = vm.allocate(cls, array_size=array_size)
#     byte_array = value.to_bytes(size, byteorder='little')
#     inst.raw_slots[:array_size] = byte_array
#     return inst


def large_or_small(r, vm):
    if SMALLINT_MIN <= r <= SMALLINT_MAX:
        return integer.create(r, vm.memory)
    length = len(hex(r)) - 2
    rb = int.to_bytes(r, byteorder="little", length=length)
    if r < 0:
        result = vm.allocate(vm.memory.largenegativeint, array_size=length)
    else:
        result = vm.allocate(vm.memory.largepositiveint, array_size=length)
    result.raw_slots[:length] = rb
    return result


def to_int(e):
    val = int(e)
    if e.kind == -1:
        return val
    if e.class_index == LargePositiveIntClass:
        return val
    if e.class_index == LargeNegativeIntClass:
        return -val
    raise Exception("Unknown problem")


def to_bytestring(e, vm):
    cls = vm.memory.bytestring
    s = vm.allocate(cls, data_len=len(e))
    mem = s.raw_slots.cast("B")
    mem[:len(e)] = bytes(e, encoding="utf-8")
    return s


def array(size, vm):
    cls = vm.memory.array
    return vm.allocate(cls, array_size=size)


def float_or_boxed(i, vm):
    value = struct.unpack(">Q", struct.pack(">d", i))[0]
    exp = (value >> 52) & 0x7FF
    if 127 <= exp <= 1023:
        return smallfloat.create(i, vm.memory)
    cls = vm.memory.boxedfloat64
    instance = vm.allocate(cls, data_len=2)
    part0 = value & 0xFFFFFFFF
    part1 = value >> instance.nb_bits
    instance[0] = part0
    instance[1] = part1
    return instance
