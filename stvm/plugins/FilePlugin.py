import os
from pathlib import Path
from ..utils import *
from ..primitives import PrimitiveFail
from ..spurobjects import ImmediateInteger as integer


def primitiveDirectoryDelimitor(cls, context, vm):
    return to_bytestring(os.path.sep, vm)


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
        mode = "r"
    else:
        mode = "w"
    f = p.open(mode)
    fileno = f.fileno()
    vm.opened_files[fileno] = f
    return integer.create(fileno, vm.memory)


def primitiveFileGetPosition(cls, fileno, context, vm):
    f = vm.opened_files[fileno.value]
    return large_or_small(f.tell(), vm)
