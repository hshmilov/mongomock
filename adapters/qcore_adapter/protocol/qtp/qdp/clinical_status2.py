from construct import Struct, Int32ul, Byte, Int16ul, Enum, Pass, Range, this, Switch, Embedded, GreedyRange, Probe, \
    Computed

from qcore_adapter.protocol.consts import UNFINISHED_PARSING_MARKER
from qcore_adapter.protocol.qtp.common import QcoreString, enum_to_mapping, CStyleEnum, QcoreInt64
from enum import auto

from qcore_adapter.protocol.qtp.qdp.clinical.alarm import AlarmClinicalStatus
from qcore_adapter.protocol.qtp.qdp.clinical.aperiodic_infusion_state import AperiodicInfusionClinicalStatus
from qcore_adapter.protocol.qtp.qdp.clinical.auto_programming_response import AutoProgramingResponseClinicalStatus
from qcore_adapter.protocol.qtp.qdp.clinical.connectivity import ConnectivityClinicalStatus
from qcore_adapter.protocol.qtp.qdp.clinical.device_settings_response import DeviceSettingsResponseClinicalStatus
from qcore_adapter.protocol.qtp.qdp.clinical.infuser import InfuserClinicalStatus
from qcore_adapter.protocol.qtp.qdp.clinical.infusion_state import InfusionStateClinicalStatus
from qcore_adapter.protocol.qtp.qdp.clinical.power import PowerClinicalStatus
from qcore_adapter.protocol.qtp.qdp.clinical.ruleset_violation import RulesetViolationClinicalStatus
from qcore_adapter.protocol.qtp.qdp.clinical.system_update import SystemUpdateClinicalStatus
from qcore_adapter.protocol.qtp.qdp.clinical_common import ClinicalMessageTypeReverseMapping


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

CSI_ITEM_TYPE = 'csi_item_type'
CSI_ITEM = 'csi_item'


def csi_to_string(ctx):
    try:
        return ClinicalStatusItemType(ctx.csi_type_numeric).name
    except:
        return str(ctx.csi_type_numeric)


ClinicalStatusItem = Struct(

    'csi_type_numeric' / Byte,
    CSI_ITEM_TYPE / Computed(csi_to_string),
    # Shared/Mednet/ClinicalItemsFactory.cpp
    CSI_ITEM / Switch(this.csi_item_type, {
        ClinicalStatusItemType.Connectivity.name: ConnectivityClinicalStatus,
        ClinicalStatusItemType.Power.name: PowerClinicalStatus,
        ClinicalStatusItemType.InfuserStatus.name: InfuserClinicalStatus,
        ClinicalStatusItemType.Alarm.name: AlarmClinicalStatus,
        ClinicalStatusItemType.RulesetViolation.name: RulesetViolationClinicalStatus,
        ClinicalStatusItemType.AutoProgramingResponse.name: AutoProgramingResponseClinicalStatus,
        ClinicalStatusItemType.Infusion.name: InfusionStateClinicalStatus,
        ClinicalStatusItemType.UpdateDeviceSettingsResponse.name: DeviceSettingsResponseClinicalStatus,
        ClinicalStatusItemType.Aperiodic_Infusion.name: AperiodicInfusionClinicalStatus,
        ClinicalStatusItemType.SystemUpdate.name: SystemUpdateClinicalStatus,
    },
        default=Struct(
        UNFINISHED_PARSING_MARKER / Pass,
        'TODO' / GreedyRange(Byte)
    )),
)

CSI_ELEMENTS = 'csi_elements'
CLINICAL_EVENT_TYPE = 'clinical_event_type'

ClinicalStatus2Message = Struct(
    'ClinicalStatus2Message' / Pass,
    'sequence_id' / QcoreInt64,
    'timestamp' / Int32ul,
    'start_record' / QcoreInt64,
    'end_record' / QcoreInt64,
    CLINICAL_EVENT_TYPE / Enum(Byte, **QdmClinicalEventReverseMapping),
    'device_context_type' / Enum(Byte, **DeviceContextReverseMapping),
    'device_operational_mode' / Byte,
    'cs2_message_type' / Enum(Byte, **ClinicalMessageTypeReverseMapping),
    # For 14.5
    'dl_name' / QcoreString,
    'dl_timestamp' / Int32ul,
    'dl_version' / QcoreString,
    'schema_version' / QcoreString,
    'items_list_size' / Int16ul,
    CSI_ELEMENTS / Range(this.items_list_size, this.items_list_size, ClinicalStatusItem),  # assert exact length
)
