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
    def create(cls, i, memory, init=False):
        if not init and i in range(-255, 255):
            return memory.integers[i + 255]
        addr = struct.unpack("Q", struct.pack("q", ((i << 3)) | 0b001 ))
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

    def __float__(self):
        return float(self.value)

    def display(self):
        return str(self.value)

    def as_float(self):
        return float(self.value)

    def as_immediate_int(self):
        return self


class ImmediateFloat(SpurObject):
    class_ = None
    number_of_slots = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kind = -4

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
        self.tab_repr = None

    @classmethod
    def create(cls, i, memory):
        addr = struct.unpack(">Q", struct.pack(">d", i))[0]
        addr = cls.rol(addr, 1, 64)
        if addr > 1:
            addr = addr - 0x7000000000000000
        addr = (addr << 3) | 0b100
        return memory.object_at(addr)

    def __getitem__(self, index):
        try:
            return ImmediateInteger.create(self.tab_repr[index], self.memory)
        except Exception:
            self.tab_repr = struct.unpack(">II", struct.pack(">d", self.value))
            return ImmediateInteger.create(self.tab_repr[index], self.memory)

    def __repr__(self):
        return f"{super().__repr__()}({self.value})"

    def __float__(self):
        return self.value

    def as_text(self):
        return f"{self.value}"

    def as_float(self):
        return self.value

    def as_immediate_int(self):
        return ImmediateInteger.create(ord(self.value), self.memory)


    def display(self):
        return str(self.value)


class ImmediateChar(SpurObject):
    class_ = None
    number_of_slots = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kind = -2

    def update(self, new_address):
        self.value = chr(new_address >> 3)
        self.class_ = self.memory.character

    @classmethod
    def create(cls, i, memory):
        addr = struct.unpack("Q", struct.pack("Q", (ord(i) << 3) | 0b010))
        addr = addr[0]
        return memory.object_at(addr)

    def __getitem__(self, index):
        raise TypeError(f"{self.__class__.__name__} don't have slots")

    def __repr__(self):
        return f"{super().__repr__()}({self.value})"

    def __eq__(self, other):
        return self.value == str(other)

    def __hash__(self):
        return hash(self.address)

    def __le__(self, other):
        return self.value <= str(other)

    def __lt__(self, other):
        return self.value < str(other)

    def __gt__(self, other):
        return self.value > str(other)

    def __ge__(self, other):
        return self.value >= str(other)

    def __and__(self, other):
        return self.value & str(other)

    def __or__(self, other):
        return self.value | str(other)

    def as_immediate_int(self):
        return ImmediateInteger.create(ord(self.value), self.memory)

    def display(self):
        return f"${self.value}"
