from construct import Struct, Enum, Byte, Int32ul, Embedded, GreedyRange

from qcore_adapter.protocol.qtp.common import CStyleEnum, enum_to_mapping
from qcore_adapter.protocol.qtp.qdp.clinical.sequence import QcoreSequence

from enum import auto


class SystemEvent(CStyleEnum):
    CASSETTE_INSTALLED_VALUE = auto()
    CASSETTE_REMOVED_VALUE = auto()
    DOOR_CLOSED_VALUE = auto()
    DOOR_OPEN_VALUE = auto()
    INFUSER_BLACKOUT_END_VALUE = auto()
    INFUSER_BLACKOUT_START_VALUE = auto()
    SEEP_DEFAULTED_VALUE = auto()
    KEYPAD_LOCK_EVENT_VALUE = auto()
    KEYPAD_SILENCED_VALUE = auto()
    KEYPAD_UNLOCKED_EVENT_VALUE = auto()


SystemUpdateClinicalStatus = Struct(
    Embedded(QcoreSequence),
    'event_type' / Enum(Byte, **enum_to_mapping(SystemEvent)),
)
