from enum import Enum
from qcore_adapter.protocol.qtp.common import enum_to_mapping


class ProtocolUnit(Enum):
    Mediator = 101  # 0x65
    DataWithCrc = 102  # 0x66
    QdpMessage = 103  # 0x67
    Qca = 104  # 0x68
    SoftwareUpdate = 202  # 0xca
    ReservedForMsgSize = 221  # 0xdd


ProtocolUnitReverseMapping = enum_to_mapping(ProtocolUnit)
