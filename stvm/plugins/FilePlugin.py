import os
from ..image_reader32 import build_int


def primitiveFileOpen(context, file_name, write_flag):
    file_name = file_name.obj.as_text()
    write_flag = write_flag.is_true

    flags = os.O_RDONLY
    if write_flag:
        flags = O_RDWR
    fd = os.open(file_name, flags)
    import ipdb; ipdb.set_trace()

    return build_int(fd, context.vm.mem)
