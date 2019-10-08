from ..image_reader32 import build_int


def primitiveStringHash(context, aString, species_hash):
    aString = aString.obj.as_text()
    species_hash = species_hash.obj.as_int()
    strin_size = len(aString)
    hash_val = species_hash  & 0xFFFFFFF
    for char in aString:
        hash_val += ord(char)
        low = hash_val & 16383
        hash_val = (0x260D * low + ((0x260D * (hash_val >> 14) + (0x0065 * low) & 16383) * 16384)) & 0x0FFFFFFF
    return build_int(hash_val, context.vm.mem)
