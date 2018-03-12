from qcore_adapter.protocol.qtp.common import CStyleEnum
from enum import auto


class PackageType(CStyleEnum):
    Software = auto()
    DrugLibrary = auto()
    IvciBarcode = auto()
