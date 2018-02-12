from construct import Struct, Embedded, Enum, Byte, Int32ul, Float64l

from protocol.qtp.common import CStyleEnum, enum_to_mapping, QcoreString
from protocol.qtp.qdp.clinical.sequence import QcoreSequence
from enum import auto


class AutoProgramingStatus(CStyleEnum):
    Queued = auto()
    Received = auto()
    FailedDelivery = auto()
    Valid = auto()
    InValid = auto()
    Rejected = auto()
    Accepted = auto()


AutoProgramingResponseClinicalStatus = Struct(
    Embedded(QcoreSequence),
    'status' / Enum(Byte, **enum_to_mapping(AutoProgramingStatus)),
    'reference_id' / Int32ul,
    'tag' / Int32ul,
    'cca_id' / Int32ul,
    'profile_id' / Int32ul,
    'reason_code' / Byte,  # TODO: looks like there should be an enum for this value
    'medication_strength' / Float64l,
    'medicaton_strength_units' / Int32ul,
    'diluent_volume' / Int32ul,
    'volume_to_be_infused' / Int32ul,
    'rate_x1000' / Float64l,
    'rate_units' / Int32ul,
    'rate_field_details' / Int32ul,
    'dose_rate' / Float64l,
    'dose_rate_units' / Int32ul,
    'dose_rate_field_details' / Int32ul,
    'patient_weight' / Int32ul,
    'dl_id' / QcoreString,
    'unkown_drug' / Byte,
    'medication_strength_field_details' / Int32ul,
    'dilient_volume_field_details' / Int32ul,
    'volume_to_be_infused_field_details' / Int32ul,
    'patient_weight_field_details' / Int32ul,
    'duration_sec' / Int32ul,
    'duration_field_details' / Int32ul
)
