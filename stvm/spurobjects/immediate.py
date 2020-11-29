from .objects import SpurObject
import struct

class ImmediateInteger(SpurObject):
    class_ = None
    number_of_slots = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kind = -1

    def update(self, new_address):
        self.value = struct.unpack("q", struct.pack("Q", new_address))[0] >> 3
        self.class_ = self.memory.smallinteger

    @classmethod
    def create(cls, i, memory):
        addr = struct.unpack("Q", struct.pack("q", ((i << 3)) | 0x01 ))
        addr = addr[0]
        return memory.object_at(addr)

    def __getitem__(self, index):
        raise TypeError(f"{self.__class__.__name__} don't have slots")

    def __repr__(self):
        return f"{super().__repr__()}({self.value})"

    def __eq__(self, other):
        return self.value == int(other)

    def __hash__(self):
        return hash(self.address)

    def __le__(self, other):
        return self.value <= int(other)

    def __lt__(self, other):
        return self.value < int(other)

    def __gt__(self, other):
        return self.value > int(other)

    def __ge__(self, other):
        return self.value >= int(other)

    def __and__(self, other):
        return self.value & int(other)

    def __or__(self, other):
        return self.value | int(other)

    def __neg__(self):
        return -self.value

    def __int__(self):
        return self.value

    def __index__(self):
        return self.value

    def display(self):
        return str(self.value)

    def as_float(self):
        return float(self.value)


class ImmediateFloat(SpurObject):
    class_ = None
    number_of_slots = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kind = -3

    @staticmethod
    def ror(n, rotations, width):
        return (2**width-1)&(n>>rotations|n<<(width-rotations))

    @staticmethod
    def rol(n, rotations, width):
        return (2**width-1)&(n<<rotations|n>>(width-rotations))

    def update(self, new_address):
        value = new_address >> 3
        if value > 1:
            value = value + 0x7000000000000000
        value = self.ror(value, 1, 64)
        value = struct.unpack(">d", struct.pack(">Q", value))[0]
        self.value = value
        self.class_ = self.memory.smallfloat64

    @classmethod
    def create(cls, i, memory):
        addr = struct.unpack(">Q", struct.pack(">d", i))[0]
        addr = cls.rol(addr, 1, 64)
        if addr > 1:
            addr = addr - 0x7000000000000000
        addr = (addr << 3) | 0x4
        return memory.object_at(addr)

    def __getitem__(self, index):
        raise TypeError(f"{self.__class__.__name__} don't have slots")

    def __repr__(self):
        return f"{super().__repr__()}({self.value})"

    def as_text(self):
        return f"{self.value}"

    def as_float(self):
        return self.value

    def display(self):
        return str(self.value)
