from construct import Struct, Int32ul, Bytes, this, Probe, Pass, Byte, Enum

from qcore_adapter.protocol.qtp.common import CStyleEnum, enum_to_mapping
from enum import auto

# QsuEraseMemoryRequest.cpp
EraseMemoryRequestMessage = Struct(
    'EraseMemoryRequestMessage' / Pass,
    'start_addr' / Int32ul,
    'end_addr' / Int32ul,
)
