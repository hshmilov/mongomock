from construct import Struct, Enum, Byte, Int32ul, Embedded, Int32sl

from qcore_adapter.protocol.qtp.qdp.clinical.sequence import QcoreSequence

UpdateResponse = Enum(Byte, Success=0, Invalid=1, Cannot=2)

DeviceSettingsResponseClinicalStatus = Struct(
    Embedded(QcoreSequence),
    'update_response' / UpdateResponse,
    'tag' / Int32sl
)
