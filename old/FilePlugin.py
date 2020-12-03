import os
from ..image_reader32 import build_int

raise Exception

def primitiveFileOpen(context, file_name, write_flag):
    file_name = file_name.obj.as_text()
    write_flag = write_flag.is_true
    flags = os.O_RDONLY
    if write_flag:
        flags = os.O_RDWR | os.O_APPEND | os.O_CREAT
    fd = os.open(file_name, flags)
    return build_int(fd, context.vm.mem)


def primitiveFileSize(context, file_id):
    file_id = file_id.obj.value
    stat = os.fstat(file_id)
    return build_int(stat.st_size, context.vm.mem)


def primitiveFileSetPosition(context, file_id, offset):
    file_id = file_id.obj.value
    offset = offset.obj.value
    os.lseek(file_id, offset, os.SEEK_SET)


def primitiveFileWrite(context, file_id, buffer, start, nb_elements):
    file_id = file_id.obj.value
    buffer = buffer.obj
    start = start.obj.value - 1
    nb_elements = nb_elements.obj.value
    for i in range(start, start + nb_elements):
        os.write(file_id, buffer[i].tobytes())


def primitiveFileClose(context, file_id):
    file_id = file_id.obj.value
    os.close(file_id)
