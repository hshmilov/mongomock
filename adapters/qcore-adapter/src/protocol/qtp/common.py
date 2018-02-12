from construct import PascalString, Byte, StringsAsBytes
import enum
from enum import auto

QTP_START = 0xBB
QTP_END = 0xCC
QTP_SIZE_MARKER = 0xDD

QcoreString = PascalString(lengthfield=Byte, encoding='utf8')


class CStyleEnum(enum.Enum):
    def _generate_next_value_(name, start, count, last_values):
        return count


def enum_to_mapping(enum_):
    return {e.name: e.value for e in list(enum_)}


class QcoreTimeUnit(CStyleEnum):
    none = auto()
    hour = auto()
    minute = auto()


class QcoreWightUnit(CStyleEnum):
    none = auto()
    kilogram = auto()


class QcoreDrugUnit(CStyleEnum):
    none = auto()
    ml = auto()
    mg = auto()
    mcg = auto()
    units = auto()
