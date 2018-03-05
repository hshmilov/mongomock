import enum

from construct import Struct, Enum, Byte, Int32ul, Embedded, Int32sl, If, this, Float64l, Pass, Int16ul, Probe, \
    GreedyRange, Check, len_, FlagsEnum, BitStruct, BitsInteger, Computed, Int16sl

from qcore_adapter.protocol.qtp.common import CStyleEnum, enum_to_mapping, QcoreString, QcoreTimeUnit, QcoreWightUnit, \
    DrugAmountUnit
from qcore_adapter.protocol.qtp.qdp.clinical.clinical_enums import InfusionEvent

from qcore_adapter.protocol.qtp.qdp.clinical.infusion_state import InfusionStateClinicalStatus
from enum import auto


class OperationalModeType(CStyleEnum):
    CONTINUOUS = auto()
    PIGGYBACK = auto()
    CONCURRENT = auto()
    BOLUS = auto()
    LOADING_DOSE = auto()
    CHANNEL_SEQUENCE = auto()
    INTERMITTENT = auto()
    MULTISTEP = auto()
    PCA = auto()
    SIMPLE = auto()
    FLUSH = auto()
    NONE = auto()
    NOT_DOCUMENTED = 255


class OperationalStatus(enum.Enum):
    Infusing = 2 ** 0
    Kvo = 2 ** 1
    KvoFinished = 2 ** 2
    Resumed = 2 ** 3
    Paused = 2 ** 4
    StoppedByUser = 2 ** 5
    StoppedByAlarm = 2 ** 6
    Completed = 2 ** 7
    Segment = 2 ** 8
    Step = 2 ** 9
    NearTermination = 2 ** 10
    BolusStarted = 2 ** 11
    BolusFinished = 2 ** 12
    Priming = 2 ** 13
    Delay = 2 ** 14
    StandBy = 2 ** 15
    Transitioning = 2 ** 16
    SwitchSource = 2 ** 17
    Programing = 2 ** 18


BolusProgrammedData = Struct(
    'BolusProgrammedData' / Pass,
    'programmed_delivery_rate' / Float64l,
    'dose_rate' / Float64l,
    'dose_rate_field_details' / Int32ul,
    'dose_rate_units' / Int16ul,
    'programmed_dose' / Float64l,
    'programmed_dose_field_details' / Int32ul,
    'programmed_dose_units' / Int16ul,
    'programmed_volume' / Float64l,
    'programmed_volume_field_details' / Int32ul,
    'programmed_duration' / Int32ul,
    'programmed_duration_field_details' / Int32ul
)


def parse_rate(rate):
    if rate == 65535:
        return 'N/A'
    try:
        weight = QcoreWightUnit(rate & 0x3).name
        time = QcoreTimeUnit((rate >> 2) & 0x3).name
        drug_unit = DrugAmountUnit((rate >> 8) & 0xf).name

        if weight == time == drug_unit:
            # 'none' ...
            return 'N/A'
        if weight == QcoreWightUnit.none.name:
            return f'{drug_unit}/{time}'

        return f'{drug_unit}/{weight}/{time}'
    except Exception as e:
        print(f'failed to parse {rate} - {e}')
        return f'Failed parsing {rate}'


AperiodicInfusionClinicalStatus = Struct(
    'AperiodicInfusionClinicalStatus' / Pass,
    'csi_infusion_state' / InfusionStateClinicalStatus,
    'infusion_event' / Enum(Int16ul, **enum_to_mapping(InfusionEvent)),
    'rate_units' / Int16ul,
    'rate_units_parsed' / Computed(lambda ctx: parse_rate(ctx.rate_units)),
    # 14.5
    'operational_status' / FlagsEnum(Int32ul, **enum_to_mapping(OperationalStatus)),  # Bitfield
    'dose_rate' / Float64l,
    'delivery_infusion_rate' / Float64l,
    'total_volume_programmed_steps' / Int32ul,
    'total_programmed_time' / Int32ul,
    'step_volume_for_programmed_steps' / Int32ul,
    'step_programmed_time_remaining' / Int32ul,
    'diluents' / Float64l,
    'dose_rate_field_details' / Int32ul,
    'dl_id' / QcoreString,
    'external_drug_id' / QcoreString,
    'drug_units' / Enum(Int16ul, **enum_to_mapping(DrugAmountUnit)),
    'cca_index' / Int16ul,
    'operational_mode' / Enum(Int16ul, **enum_to_mapping(OperationalModeType)),
    # drug rule id
    'drug_rule_id' / Int16ul,
    'medication_strength' / Float64l,
    'patient_weight' / Float64l,
    'cumulative_volume' / Int32ul,
    # 14.15
    'is_bolus' / Byte,
    'bolus_programmed_data' / If(lambda ctx: ctx.is_bolus > 0, BolusProgrammedData),
    'programmed_modes' / Int32ul,
    # 14.5
    'number_of_programmed_steps' / Int32ul,
    'programed_steps_volume_field_details' / Int32ul,
    'current_delivery_infusion_rate' / Float64l,
    'unknown_drug' / Byte,  # bool in sources...
    'programmed_steps_remaining_field_details' / Int32ul,
    'patient_weight_field_details' / Int32ul,
    'distal_occlusion_threshold' / Int32ul,
    'proximal_occlusion_threshold' / Int32ul,
)
