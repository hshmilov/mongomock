from construct import Struct, Int32ul, Bytes, this, Probe, Pass, Byte, Enum

from qcore_adapter.protocol.qtp.common import CStyleEnum, enum_to_mapping
from enum import auto

# QsuValidateCrcRequest.cpp
ValidateCrcRequestMessage = Struct(
    'ValidateCrcRequestMessage' / Pass,
    'start_addr' / Int32ul,
    'version_addr' / Int32ul,
)
