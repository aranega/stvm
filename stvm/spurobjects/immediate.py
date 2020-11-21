from .objects import SpurObject

class ImmediateInteger(SpurObject):
    class_ = None
    number_of_slots = 0

    def update(self, new_address):
        self.value = struct.unpack("q", struct.pack("q", new_address))[0] >> 3
        self.class_ = self.memory.smallinteger

    def __getitem__(self, index):
        raise TypeError("ImmediateInteger don't have slots")

    def __repr__(self):
        return f"{super().__repr__()}({self.value})"

    def __eq__(self, other):
        if other.__class__ is not self.__class__:
            return False
        return self.value == other.value

    def __hash__(self):
        return object.__hash__(self)

    def __le__(self, other):
        if other.__class__ is not self.__class__:
            return False
        return self.value <= other.value

    def __lt__(self, other):
        if other.__class__ is not self.__class__:
            return False
        return self.value < other.value

    def __gt__(self, other):
        if other.__class__ is not self.__class__:
            return False
        return self.value > other.value

    def __ge__(self, other):
        if other.__class__ is not self.__class__:
            return False
        return self.value >= other.value

    def __and__(self, other):
        return self.value & other

    def __or__(self, other):
        return self.value | other

    def as_int(self):
        return self.value
