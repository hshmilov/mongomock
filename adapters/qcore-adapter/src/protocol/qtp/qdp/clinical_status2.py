from construct import Struct, Int32ul, Byte, Int16ul, Enum, Pass, Range, this, Switch, Embedded
from protocol.qtp.common import QcoreString, enum_to_mapping, CStyleEnum
from enum import auto

from protocol.qtp.qdp.clinical.alarm import AlarmClinicalStatus
from protocol.qtp.qdp.clinical.auto_programming_response import AutoProgramingResponseClinicalStatus
from protocol.qtp.qdp.clinical.connectivity import ConnectivityClinicalStatus
from protocol.qtp.qdp.clinical.infuser import InfuserClinicalStatus
from protocol.qtp.qdp.clinical.infusion_state import InfusionClinicalStatus
from protocol.qtp.qdp.clinical.power import PowerClinicalStatus
from protocol.qtp.qdp.clinical.ruleset_violation import RulesetViolationClinicalStatus
from protocol.qtp.qdp.clinical_common import ClinicalMessageTypeReverseMapping


class ClinicalEvent(CStyleEnum):
    CompleteStatus = auto()
    PowerUpdate = auto()
    LogUpdate = auto()
    AlarmUpdate = auto()
    InfusionUpdate = auto()
    RulesetViolationUpdate = auto()
    CommandResponseUpdate = auto()
    SystemUpdate = auto()
    ConnectivityUpdate = auto()


QdmClinicalEventReverseMapping = enum_to_mapping(ClinicalEvent)


class DeviceContext(CStyleEnum):
    Sleeping = auto()
    Idling = auto()
    Infusing = auto()
    Alarming = auto()
    Updating = auto()
    Malfunction = auto()


DeviceContextReverseMapping = enum_to_mapping(DeviceContext)


class ClinicalStatusItemType(CStyleEnum):
    Power = auto()
    Connectivity = auto()
    InfuserStatus = auto()
    Alarm = auto()
    RulesetViolation = auto()
    AutoProgramingResponse = auto()
    Infusion = auto()
    Aperiodic_Infusion = auto()
    PackageDeployResponse = auto()
    SystemUpdate = auto()
    CcaUpdate = auto()
    CommandResponse = auto()
    Multistep = auto()
    UpdateDeviceSettingsResponse = auto()


ClinicalStatusItemTypeReverseMapping = enum_to_mapping(ClinicalStatusItemType)

QcoreInt64 = Struct(
    'high' / Int32ul,
    'low' / Int32ul
)

ClinicalStatusItem = Struct(
    'csi_item_type' / Enum(Byte, **ClinicalStatusItemTypeReverseMapping),
    'csi_item' / Switch(this.csi_item_type, {
        ClinicalStatusItemType.Connectivity.name: ConnectivityClinicalStatus,
        ClinicalStatusItemType.Power.name: PowerClinicalStatus,
        ClinicalStatusItemType.InfuserStatus.name: InfuserClinicalStatus,
        ClinicalStatusItemType.Alarm.name: AlarmClinicalStatus,
        ClinicalStatusItemType.RulesetViolation.name: RulesetViolationClinicalStatus,
        ClinicalStatusItemType.AutoProgramingResponse.name: AutoProgramingResponseClinicalStatus,
        ClinicalStatusItemType.Infusion.name: InfusionClinicalStatus
    })
)

ClinicalStatus2Message = Struct(
    'ClinicalStatus2Message' / Pass,
    'sequence_id' / QcoreInt64,
    'timestamp' / Int32ul,
    'start_record' / QcoreInt64,
    'end_record' / QcoreInt64,
    'clinical_event_type' / Enum(Byte, **QdmClinicalEventReverseMapping),
    'device_context_type' / Enum(Byte, **DeviceContextReverseMapping),
    'device_operational_mode' / Byte,
    'cs2_message_type' / Enum(Byte, **ClinicalMessageTypeReverseMapping),
    # For 14.5
    'dl_name' / QcoreString,
    'dl_timestamp' / Int32ul,
    'dl_version' / QcoreString,
    'schema_version' / QcoreString,
    'items_list_size' / Int16ul,
    'csi_elements' / Range(this.items_list_size, this.items_list_size, ClinicalStatusItem)
)
