from construct import Struct, Int32ul, Bytes, this, Probe, Pass, Byte, Enum

# QsuCompareFileVersionRequest.cpp
CompareFileVersionRequestMessage = Struct(
    'CompareFileVersionRequestMessage' / Pass,
    'version_address' / Int32ul,
    'version_data' / Bytes(16),
)
