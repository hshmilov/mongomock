from construct import Struct, Enum, Byte, Embedded, Int16ul, Int32ul

from enum import auto

from protocol.qtp.common import CStyleEnum, enum_to_mapping
from protocol.qtp.qdp.clinical.sequence import QcoreSequence


class RulesetType(CStyleEnum):
    DoseRate = auto()  # RS_DOSE_LIMIT
    Vtbi = auto()  # RS_AMOUNT_LIMIT
    Duration = auto()  # RS_DURATION_LIMIT
    SystemMaximumParameter = auto()  # obsolete
    SystemMaxDuration = auto()  # RS_SYSTEM_MAXIMUM_DURATION
    MultiStepTime = auto()  # RS_CCA_MAXIMUM_DURATION
    CcaMaxVtbi = auto()  # RS_CCA_MAXIMUM_VTBI
    MaxBolusVtbi = auto()  # RS_MAX_AMOUNT_LIMIT
    PatientWeight = auto()  # RS_PATIENT_WEIGHT


class LimitType(CStyleEnum):
    e_LimitType_Soft = auto()
    e_LimitType_Hard = auto()
    e_LimitType_Cca = auto()
    e_LimitType_System = auto()


class LimitBoundType(CStyleEnum):
    e_LimitBoundType_High = auto()
    e_LimitBoundType_Low = auto()


RulesetViolationClinicalStatus = Struct(
    Embedded(QcoreSequence),
    'cca_index' / Int16ul,
    'drug_rule_id' / Int16ul,
    'infusion_id' / Int16ul,
    'ruleset_type' / Enum(Int16ul, **enum_to_mapping(RulesetType)),
    'limit_type' / Enum(Int16ul, **enum_to_mapping(LimitType)),
    'limit_bound_type' / Enum(Int16ul, **enum_to_mapping(LimitBoundType)),
    'rate_units' / Int16ul,
    'time_units' / Int16ul,
    'limit_value' / Int32ul,
    'drug_library_id', QcoreSequence,
    'rule_value' / Int32ul,
    'is_bolus' / Byte,
    'line_id' / Byte,
    # for 14.5
    'was_overriden' / Byte,
    'step' / Byte,
    'segment' / Byte,
)
