from math import ceil
from ..spurobjects import ImmediateInteger as integer


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


def large_or_small(value, vm):
    if SMALLINT_MIN <= value <= SMALLINT_MAX:
        return integer.create(value, vm.memory)
    return large(value, value < 0, vm)


def large(r, neg, vm):
    length = ceil((len(hex(r)) - 2) / 2)
    if neg:
        r = -r
        result = vm.allocate(vm.memory.largenegativeint, array_size=length)
    else:
        result = vm.allocate(vm.memory.largepositiveint, array_size=length)
    rb = int.to_bytes(r, byteorder="little", length=length)
    result.raw_slots = rb
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
