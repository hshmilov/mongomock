from construct import Struct, Enum, Byte, Int32ul, Embedded, Int32sl, If, this, Float64l

from protocol.qtp.qdp.clinical.sequence import QcoreSequence
from protocol.qtp.qdp.clinical_common import ClinicalMessageTypeReverseMapping

InfusionClinicalStatus = Struct(
    Embedded(QcoreSequence),
    'message_type' / Enum(Byte, **ClinicalMessageTypeReverseMapping),
    'auto_program_reference_id' / Int32ul,
    'channel_id' / Int32sl,
    'current_step_number' / Byte,
    'current_step_time_remaining' / Int32ul,
    'delayed_time_to_start' / Int32sl,
    'distal_pressure' / Int32sl,
    'infusion_id' / Int32ul,
    'infusion_segment_id' / Int32sl,
    'line_id' / Int32sl,
    'proximal_pressure' / Int32sl,
    'step_volume_delivered' / Int32ul,
    'step_volume_remaining' / Int32ul,
    'total_volume_delivered' / Int32ul,
    'total_volume_remaining' / Int32ul,
    'total_time_remaining' / Int32ul,
    # 14.5 ######
    # this part from 14
    'is_bolus' / Byte,
    'bolus_data' / If(this.is_bolus, Struct(
        'delivered_amount' / Float64l,
        'delivered_volume' / Float64l,
        'remaining_duration' / Int32ul
    )),
    # 14.5 again
    'volume_delivered_since_last_start' / Int32sl,
    'total_bag_volume_delivered' / Int32sl,
    'distal_occlusion_threshold' / Int32sl,
    'proxima_occlusion_threshold' / Int32sl,
    'shift_total_volume_delivered' / Int32sl,
    'cummulative_volume' / Int32sl,
)
