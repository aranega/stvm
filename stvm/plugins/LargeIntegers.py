from ..spurobjects import ImmediateInteger as integer
from ..utils import *


LargeNegativeIntClass = 32
LargePositiveIntClass = 33


def primDigitSubtract(self, other, context, vm):
    return integer.create(self.value - other.value, vm.memory)


def primDigitCompare(self, arg, context, vm):
    a = to_int(self)
    b = to_int(arg)
    if a < b:
        res = -1
    elif a == b:
        res = 0
    elif a > b:
        res = 1
    return integer.create(res, vm.memory)


def primNormalizeNegative(self, context, vm):
    if self.class_index == LargeNegativeIntClass:
        return self
    import ipdb; ipdb.set_trace()


def primNormalizePositive(self, context, vm):
    if self.class_index == LargePositiveIntClass:
        return self
    import ipdb; ipdb.set_trace()


def primDigitAdd(self, arg, context, vm):
    a = to_int(self)
    b = to_int(arg)
    r = a + b
    return large(r, r < 0 , vm)


def primDigitDivNegative(self, arg, neg, context, vm):
    a = to_int(self)
    b = to_int(arg)
    r = a // b
    return large(r, neg is vm.memory.true, vm)


def primDigitMultiplyNegative(self, arg, neg, context, vm):
    a = to_int(self)
    b = to_int(arg)
    r = a * b
    return large(r, neg is vm.memory.true, vm)



def primDigitBitShiftMagnitude(self, shift, context, vm):
    v = to_int(self)
    shift = to_int(shift)
    neg = v < 0
    if neg:
        v = -v
    if shift > 0:
        v <<= shift
    else:
        v >>= -shift
    if neg:
        v = -v
    return large_or_small(v, vm)


def large_or_small(value, vm):
    if SMALLINT_MIN <= value <= SMALLINT_MAX:
        return integer.create(value, vm.memory)
    return large(value, value < 0, vm)


def large(r, neg, vm):
    length = len(hex(r)) - 2
    if neg:
        r = -r
        result = vm.allocate(vm.memory.largenegativeint, data_len=length)
    else:
        result = vm.allocate(vm.memory.largepositiveint, data_len=length)
    rb = int.to_bytes(r, byteorder="little", length=length)
    result.raw_slots[:length] = rb
    return result
