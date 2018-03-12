from enum import auto
import binascii
from construct import Struct, Pass, Int32ul, Int16ul, Bytes, this, RawCopy, Byte, Check, Switch, Enum, Tell, Pointer, \
    Checksum, Embedded, Sequence, Probe, Seek, Peek, Computed

from qcore_adapter.protocol.consts import PUMP_SERIAL
from qcore_adapter.protocol.qtp.common import enum_to_mapping, CStyleEnum, ChecksumHeader
from qcore_adapter.protocol.qtp.data_with_crc import DataWithCrcHeader
from qcore_adapter.protocol.qtp.qdp.qdp_message_types import QdpMessageTypesReverseMapping
from qcore_adapter.protocol.qtp.qtp_protocol_units import ProtocolUnit, ProtocolUnitReverseMapping


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

DataWithCrcAck = Struct(
    Embedded(DataWithCrcHeader),
    'protocol' / Enum(Int16ul, **ProtocolUnitReverseMapping),
    'operational_code' / Enum(Int16ul, **QdpMessageTypesReverseMapping),
    'data' / Enum(Byte, **AcknowledgeValuesReverseMapping),
    Check(this.size == 5)
)

QcaHeader = Struct(
    'QcaHeader' / Pass,
    Embedded(ChecksumHeader),
    'qca_protocol_unit' / Enum(Byte, **ProtocolUnitReverseMapping),
    'qca_payload' / Switch(this.qca_protocol_unit, {
        ProtocolUnit.DataWithCrc.name: DataWithCrcAck
    }),
)
