from enum import auto
import binascii
import construct

from protocol.consts import PUMP_SERIAL
from protocol.qtp.common import enum_to_mapping, CStyleEnum
from protocol.qtp.qdp.qdp_message_types import QdpMessageTypesReverseMapping
from protocol.qtp.qtp_protocol_units import ProtocolUnit, ProtocolUnitReverseMapping


class AcknowledgeValues(CStyleEnum):
    NoData = auto()
    SoftwareQueued = auto()  # Software Queued
    SoftwarePending = auto()  # Software Pending
    SoftwareInstalling = auto()  # Software Installing
    SoftwareComplete = auto()  # Software Complete
    SoftwareError = auto()  # Software Error
    DrugLibraryQueued = auto()  # Drug Library Queued
    DrugLibraryPending = auto()  # Drug Library Pending
    DrugLibraryInstalling = auto()  # Drug Library Installing
    DrugLibraryComplete = auto()  # Drug Library Complete
    DrugLibraryError = auto()  # Drug Library Error
    PumpIsBusy = auto()  # Pump is busy
    AutoProgramQueued = auto()  # AutoProgram Queued
    AutoProgramReceived = auto()  # AutoProgram Received
    AutoProgramAccepted = auto()  # AutoProgram Accepted
    AutoProgramFailedDelivery = auto()  # AutoProgram FailedDelivery
    AutoProgramInValid = auto()  # AutoProgram InValid
    AutoProgramRejected = auto()  # AutoProgram Rejected
    AutoProgramValid = auto()  # AutoProgram Valid


AcknowledgeValuesReverseMapping = enum_to_mapping(AcknowledgeValues)


def checksum256(st):
    return sum(st) % 256


QcaAck = construct.Struct(
    'QcaAck' / construct.Pass,
    'protocol' / construct.Enum(construct.Int16ul, **ProtocolUnitReverseMapping),
    'operational_code' / construct.Enum(construct.Int16ul, **QdpMessageTypesReverseMapping),
    'data' / construct.Enum(construct.Byte, **AcknowledgeValuesReverseMapping),
)

DataWithCrc = construct.Struct(
    'DataWithCrc' / construct.Pass,
    'crc32' / construct.Int32ul,
    'size' / construct.Const(5, construct.Int16ul),
    construct.Embedded(construct.RawCopy(QcaAck)),  # TODO: flatten somehow?
    construct.Check(lambda ctx: binascii.crc32(ctx.data) == ctx.crc32)  # todo - make this generated
)

QcaHeader = construct.Struct(
    'QcaHeader' / construct.Pass,
    'header' / construct.RawCopy(construct.Struct(  # TODO: flatten somehow?
        'following_message_type' / construct.Byte,
        PUMP_SERIAL / construct.Int32ul,
        'protocol_version' / construct.Int32ul,
    )),
    'checksum' / construct.Byte,
    construct.Check(lambda ctx: ctx.checksum == checksum256(ctx.header.data)),  # todo make this generated
    'qca_protocol_unit' / construct.Enum(construct.Byte, **ProtocolUnitReverseMapping),
    'qca_payload' / construct.Switch(construct.this.qca_protocol_unit, {
        ProtocolUnit.DataWithCrc.name: DataWithCrc
    })
)
