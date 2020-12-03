from spurobjects.immediate import ImmediateInteger as integer


def primitiveStringHash(cls, aString, species_hash, context, vm):
    aString = aString.as_text()
    species_hash = species_hash.value
    hash_val = species_hash  & 0xFFFFFFF
    for char in aString:
        hash_val += ord(char)
        low = hash_val & 16383
        hash_val = (0x260D * low + ((0x260D * (hash_val >> 14) + (0x0065 * low) & 16383) * 16384)) & 0x0FFFFFFF
    return integer.create(hash_val, vm.memory)
