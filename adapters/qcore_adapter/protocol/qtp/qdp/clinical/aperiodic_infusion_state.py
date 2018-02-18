from construct import Struct, Enum, Byte, Int32ul, Embedded, Int32sl, If, this, Float64l

from qcore_adapter.protocol.qtp.qdp.clinical.infusion_state import InfusionClinicalStatus
from qcore_adapter.protocol.qtp.qdp.clinical.sequence import QcoreSequence
from qcore_adapter.protocol.qtp.qdp.clinical_status2 import ClinicalMessageTypeReverseMapping

AperiodicInfusionClinicalStatus = Struct(
    Embedded(InfusionClinicalStatus),
    # TODO: fnish this guy...
)
