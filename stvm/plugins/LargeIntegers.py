from spurobjects.immediate import ImmediateInteger

def primDigitSubtract(self, other, context, vm):
    return ImmediateInteger.create(self.value - other.value, vm.memory)


def primDigitCompare(self, other, context, vm):
    if self.value < other.value:
        res = -1
    elif self.value == other.value:
        res = 0
    elif self.value > other.value:
        res = 1
    return ImmediateInteger.create(res, vm.memory)
