from ..spurobjects import ImmediateInteger as integer
from ..primitives import PrimitiveFail


def primitiveStringHash(*args, context, vm):
    *cls, string, species_hash = args
    string = string.as_text()
    species_hash = species_hash.value
    hash_val = species_hash  & 0xFFFFFFF
    for char in string:
        hash_val += ord(char)
        low = hash_val & 16383
        hash_val = (0x260D * low + ((0x260D * (hash_val >> 14) + (0x0065 * low) & 16383) * 16384)) & 0x0FFFFFFF
    return integer.create(hash_val, vm.memory)


def primitiveIndexOfAsciiInString(cls, byte, string, start, context, vm):
    if start.value < 0:
        return integer.create(0, vm.memory)

    try:
        index = string.as_text().index(chr(byte))
        return integer.create(index, vm.memory)
    except Exception:
        return integer.create(0, vm.memory)


def primitiveDecompressFromByteArray(cls, bm, ba, index, context, vm):
    i = index.value - 1
    end = len(ba) - 1
    k = 0
    past_end = len(bm)
    while i <= end:
        v = ba[i].value
        i += 1
        if v > 223:
            if v <= 254:
                v = (v - 224) * 256 + ba[i].value
                i += 1
            else:
                v = 0
                for _ in range(4):
                    v = (v << 8) + ba[i].value
                    i += 1
        n = v >> 2
        if k + n > past_end:
            raise PrimitiveFail
        code = v & 0b11
        if code == 3:
            for _ in range(n):
                data = 0
                for _ in range(4):
                    data = (data << 8) | ba[i].value
                    i += 1
                bm[k] = integer.create(data, vm.memory)
                k += 1
        elif code == 2:
            data = 0
            for _ in range(4):
                data = (data << 8) | ba[i].value
                i += 1
            for _ in range(n):
                bm[k] = integer.create(data, vm.memory)
                k += 1
        elif code == 1:
            data = ba[i].value
            i += 1
            data = data | (data << 8)
            data = data | (data << 16)
            for _ in range(n):
                bm[k] = integer.create(data, vm.memory)
                k += 1
        elif code == 0:
            ...  # skip


def primitiveFindSubstring(cls, key, body, start, match_table, context, vm):
    # TODO Use the match_table?
    try:
        start = start.value - 1
        index = body.as_text()[start:].index(key.as_text())
        # we add 1 because the result go back to ST
        return integer.create(index + start + 1, vm.memory)
    except Exception:
        return integer.create(0, vm.memory)


def primitiveCompareString(cls, s1, s2, order, context, vm):
    s1 = s1.as_text()
    s2 = s2.as_text()
    len1 = len(s1)
    len2 = len(s2)
    for i in range(min(len1, len2)):
        c1 = order.raw_at(ord(s1[i])) + 1
        c2 = order.raw_at(ord(s2[i])) + 1
        if c1 != c2:
            if c1 < c2:
                return integer.create(1, vm.memory)
            else:
                return integer.create(1, vm.memory)
    if len1 == len2:
        return integer.create(2, vm.memory)
    if len1 < len2:
        return integer.create(1, vm.memory)
    return integer.create(3, vm.memory)


def primitiveFindFirstInString(cls, string, inclusionMap, start, context, vm):
    raise PrimitiveFail
