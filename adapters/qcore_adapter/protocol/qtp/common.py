from construct import PascalString, Byte, StringsAsBytes, Struct, Int32ul
import enum
from enum import auto

QTP_START = 0xBB
QTP_END = 0xCC
QTP_SIZE_MARKER = 0xDD

QcoreString = PascalString(lengthfield=Byte, encoding='utf8')

QcoreInt64 = Struct(
    'high' / Int32ul,
    'low' / Int32ul
)


class CStyleEnum(enum.Enum):
    def _generate_next_value_(name, start, count, last_values):
        return count


def enum_to_mapping(enum_):
    return {e.name: e.value for e in list(enum_)}


class QcoreTimeUnit(CStyleEnum):
    none = auto()
    hr = auto()
    minute = auto()
    day = auto()


class QcoreWightUnit(CStyleEnum):
    none = auto()
    kg = auto()
    m2 = auto()


class DrugAmountUnit(enum.Enum):
    none = 0x00
    ml = 0x01  # mL
    mg = 0x02  # mg
    mcg = 0x03  # mcg
    units = 0x04  # Units
    nanogr = 0x05  # nanog
    mEq = 0x06  # mEq
    gr = 0x07  # grams
    mmol = 0x08  # mmol
    millionunits = 0x09  # MillionUnits
    milliunits = 0x0A,  # mUnits
    ltrs = 0x0B  # ltrs
