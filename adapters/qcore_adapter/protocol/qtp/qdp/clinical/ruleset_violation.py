from construct import Struct, Enum, Byte, Embedded, Int16ul, Int32ul, Probe, Pass, GreedyRange, Int16sl

from enum import auto

from qcore_adapter.protocol.qtp.common import CStyleEnum, enum_to_mapping, QcoreString
from qcore_adapter.protocol.qtp.qdp.clinical.sequence import QcoreSequence


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
    Soft = auto()
    Hard = auto()
    Cca = auto()
    System = auto()


class LimitBoundType(CStyleEnum):
    High = auto()
    Low = auto()


RulesetViolationClinicalStatus = Struct(
    'RulesetViolationClinicalStatus' / Pass,
    Embedded(QcoreSequence),

    'cca_index' / Int16sl,
    'drug_rule_id' / Int16ul,

    'infusion_id' / Int32ul,

    'ruleset_type' / Enum(Int16ul, **enum_to_mapping(RulesetType)),
    'limit_type' / Enum(Int16ul, **enum_to_mapping(LimitType)),
    'limit_bound_type' / Enum(Int16ul, **enum_to_mapping(LimitBoundType)),
    'rate_units' / Int16ul,
    'time_units' / Int16ul,

    'limit_value' / Int32ul,

    'drug_library_id' / QcoreString,

    'rule_value' / Int32ul,
    'is_bolus' / Byte,
    'line_id' / Byte,

    # for 14.5
    'was_overriden' / Byte,
    'step' / Byte,
    'segment' / Byte,

)
