from enum import auto

from protocol.qtp.common import CStyleEnum, enum_to_mapping


class ClinicalMessageType(CStyleEnum):
    Periodic = auto()
    Aperiodic = auto()


ClinicalMessageTypeReverseMapping = enum_to_mapping(ClinicalMessageType)
