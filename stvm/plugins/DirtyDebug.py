from pathlib import Path
from ..spurobjects import ImmediateInteger as integer
from builtins import print as python_print


def open_file_mode(cls, filename, mode, context, vm):
    p = Path(filename.as_text())
    f = p.open(mode.as_text())
    f.seek(0)
    fileno = f.fileno()
    vm.opened_files[fileno] = (p, f)
    stf = vm.allocate(cls)
    stf[0] = integer.create(fileno, vm.memory)
    return stf


def write_file(stf, string, context, vm):
    fileno = stf[0].value
    _, f = vm.opened_files[fileno]
    f.write(string.as_text())


def close_file(stf, context, vm):
    fileno = stf[0].value
    _, f = vm.opened_files[fileno]
    f.close()
    return vm.memory.nil


def print(cls, string, context, vm):
    python_print()
    python_print()
    python_print(string.as_text())
    python_print()
    python_print()
