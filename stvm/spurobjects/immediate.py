from .objects import SpurObject
import struct

class ImmediateInteger(SpurObject):
    class_ = None
    number_of_slots = 0

    def update(self, new_address):
        self.value = struct.unpack("q", struct.pack("Q", new_address))[0] >> 3
        self.class_ = self.memory.smallinteger

    @classmethod
    def create(cls, i, memory):
        addr = struct.unpack("Q", struct.pack("q", ((i << 3)) | 0x01 ))
        addr = addr[0]
        return cls(addr, memory)

    def __getitem__(self, index):
        raise TypeError("ImmediateInteger don't have slots")

    def __repr__(self):
        return f"{super().__repr__()}({self.value})"

    def __eq__(self, other):
        return self.value == int(other)

    def __hash__(self):
        return object.__hash__(self)

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
