import struct
from ..primitives import PrimitiveFail
from ..utils import *


def primitiveAt(self, index, context, vm):
    v = self.raw_bytes_at(index.value - 1)
    f = struct.unpack("<f", v)[0]
    return float_or_boxed(f, vm)


def primitiveAtPut(self, index, value, context, vm):
    self[index.value - 1] = struct.pack("<f", value)
    return value
