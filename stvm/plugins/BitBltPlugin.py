from ..spurobjects import ImmediateInteger as integer
from ..utils import *
from ..primitives import PrimitiveFail



def primitiveCopyBits(self, context, vm):
    print("Buggy implementation of copybits")
    dst = self[0][0]
    src = self[1][0]
    width = self[6].value
    height = self[7].value
    for i in range(height):
        for j in range(width):
            dst.raw_slots[i * height + j] = src.raw_slots[i * height + j]
