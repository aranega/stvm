from ..utils import *


def primitiveCanWriteImage(*args, context, vm):
    return False


def primitiveGetSecureUserDirectory(manager, context, vm):
    image_file = vm.image.file
    image_name = image_file.stem
    secure_user_dir = image_file.parent / image_name / 'user_secure'
    return to_bytestring(str(secure_user_dir), vm)


def primitiveGetUntrustedUserDirectory(manager, context, vm):
    image_file = vm.image.file
    image_name = image_file.stem
    untrusted = image_file.parent / image_name / 'untrusted'
    return to_bytestring(str(untrusted), vm)
