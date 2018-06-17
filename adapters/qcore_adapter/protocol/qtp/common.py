from construct import PascalString, Byte, StringsAsBytes, Struct, Int32ul, Tell, Peek, Seek, this, Check, Bytes, \
    Pointer, Checksum, Computed, Rebuild, Construct, Embedded
import enum
from enum import auto

from qcore_adapter.protocol.consts import PUMP_SERIAL

QTP_START = 0xBB
QTP_END = 0xCC
QTP_SIZE_MARKER = 0xDD

QcoreString = PascalString(lengthfield=Byte, encoding='utf8')

QcoreInt64 = Struct(
    'high' / Int32ul,
    'low' / Int32ul
)


def checksum256(st):
    return sum(st) % 256


def from_context_to_bytes(ctx):
    bytes = ChecksummedFields.build(ctx)
    return bytes


ChecksummedFields = Struct(
    'following_message_type' / Byte,
    PUMP_SERIAL / Int32ul,
    'protocol_version' / Int32ul,
)

ChecksumHeader = Struct(
    Embedded(ChecksummedFields),
    'checksum_buff' / Computed(from_context_to_bytes),
    'checksum' / Checksum(Byte,
                          checksum256,
                          this.checksum_buff))


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
