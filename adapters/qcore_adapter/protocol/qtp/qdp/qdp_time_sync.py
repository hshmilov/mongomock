from construct import Struct, Int32ul, Pass, this
from qcore_adapter.protocol.qtp.common import QcoreString

TimeSyncMessage = Struct(
    'TimeSyncMessage' / Pass,
    'device_id' / QcoreString,
    'client_rtc' / Int32ul,
    'client_timezone' / QcoreString,
    'server_rtc' / Int32ul,
    'server_timezone' / QcoreString
)
