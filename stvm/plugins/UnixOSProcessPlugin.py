import os
from ..utils import *


def primitiveGetCurrentWorkingDirectory(cls, context, vm):
    return to_bytestring(os.getcwd(), vm)
