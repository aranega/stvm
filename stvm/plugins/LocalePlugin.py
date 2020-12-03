from math import ceil
from datetime import datetime
from spurobjects.immediate import ImmediateInteger as integer


def primitiveTimezoneOffset(self, context, vm):
    r = ceil((datetime.now() - datetime.utcnow()).total_seconds() / 60)
    return integer.create(r, vm.memory)
