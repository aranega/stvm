import os
from pathlib import Path
from ..utils import *
from ..primitives import PrimitiveFail
from ..spurobjects import ImmediateInteger as integer
from ..spurobjects import ImmediateChar as char


def primitiveDirectoryDelimitor(cls, context, vm):
    return char.create(os.path.sep, vm.memory)


def primitiveDirectoryLookup(cls, full_path, index, context, vm):
    p = Path(full_path.as_text())
    if not p.exists():
        raise PrimitiveFail

    if p.is_dir():
        try:
            p = list(p.iterdir())[index.value - 1]
        except Exception:
            return vm.memory.nil

    is_dir = vm.memory.true if p.is_dir() else vm.memory.false
    stats = p.stat()
    size = integer.create(stats.st_size, vm.memory)
    ctime = integer.create(int(stats.st_ctime), vm.memory)
    mtime = integer.create(int(stats.st_mtime), vm.memory)

    result = array(5, vm)
    result[0] = to_bytestring(p.name, vm)
    result[1] = ctime
    result[2] = mtime
    result[3] = is_dir
    result[4] = size
    return result


def primitiveFileOpen(cls, file_name, writable, context, vm):
    p = Path(file_name.as_text())
    if writable is vm.memory.false:
        if not p.exists():
            return vm.memory.nil
        mode = "rb"
    else:
        mode = "rb+"
    f = p.open(mode)
    fileno = f.fileno()
    vm.opened_files[fileno] = f
    return integer.create(fileno, vm.memory)


def primitiveFileGetPosition(cls, fileno, context, vm):
    f = vm.opened_files[fileno.value]
    return large_or_small(f.tell(), vm)


def primitiveFileWrite(f, fileno, string, start, count, context, vm):
    f = vm.opened_files[fileno.value]
    start = start.value - 1
    countv = count.value
    f.write(string.raw_slots[start:start + countv])
    return count


def primitiveDirectoryEntry(cls, path, name, context, vm):
    p = Path(path.as_text()) / name.as_text()
    if not p.exists():
        raise PrimitiveFail

    is_dir = vm.memory.true if p.is_dir() else vm.memory.false
    stats = p.stat()
    size = integer.create(stats.st_size, vm.memory)
    ctime = integer.create(int(stats.st_ctime), vm.memory)
    mtime = integer.create(int(stats.st_mtime), vm.memory)

    result = array(5, vm)
    result[0] = to_bytestring(p.name, vm)
    result[1] = ctime
    result[2] = mtime
    result[3] = is_dir
    result[4] = size
    return result


def primitiveFileRead(stream, fileno, dst, index, count, context, vm):
    f = vm.opened_files[fileno.value]
    nb_bytes = dst.nb_bits // 8
    index = index.value - 1
    count = count.value
    buffer = f.read(count * nb_bytes)
    nb_read = len(buffer) // nb_bytes
    dst.raw_slots[:nb_read] = buffer
    return integer.create(nb_read, vm.memory)
