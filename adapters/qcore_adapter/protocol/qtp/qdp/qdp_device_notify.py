from construct import Struct, Int32ul, Pass, this, Byte, Enum
from qcore_adapter.protocol.qtp.common import QcoreString, CStyleEnum, enum_to_mapping
from enum import auto


class DeviceNotificationReasonType(CStyleEnum):
    APIncomplete = auto()
    APCorrupted = auto()
    UnrecognizedDrugLibrary = auto()
    UnknownCdlForAutoProgram = auto()


DeviceNotifyMessage = Struct(
    'notification_type' / Enum(Byte, **enum_to_mapping(DeviceNotificationReasonType))
)
