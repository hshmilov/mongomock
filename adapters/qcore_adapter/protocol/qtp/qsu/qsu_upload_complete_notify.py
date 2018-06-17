from construct import Struct, Int32ul, Bytes, this, Probe, Pass, Byte, Enum

from qcore_adapter.protocol.qtp.common import CStyleEnum, enum_to_mapping
from enum import auto
from qcore_adapter.protocol.qtp.qsu.consts import PackageType, UploadResult

# QsuUploadCompleteNotify.cpp
UploadCompleteNotifyMessage = Struct(
    'UploadCompleteNotifyMessage' / Pass,
    'package_type' / Enum(Byte, **enum_to_mapping(PackageType)),
    'end_addr' / Enum(Byte, **enum_to_mapping(UploadResult))
)
