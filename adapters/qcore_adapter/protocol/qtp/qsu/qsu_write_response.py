from construct import Struct, Int32ul, Bytes, this, Probe, Pass, Byte, Enum

# QsuWriteResponse.cpp
WriteResponseMessage = Struct(
    'WriteResponseMessage' / Pass,
    'response' / Enum(Byte, Ok=0, HardwareFailure=1, MemoryNotErased=2),
    'start_addr' / Int32ul,
    'data_size' / Int32ul,
)
