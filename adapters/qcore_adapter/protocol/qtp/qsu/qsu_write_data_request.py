from construct import Struct, Int32ul, Bytes, this, Probe, Pass

# QsuWriteDataRequest.cpp
WriteDataRequestMessage = Struct(
    'WriteDataRequestMessage' / Pass,
    'start_addr' / Int32ul,
    'data_size' / Int32ul,
    'data_buff' / Bytes(this.data_size),
)
