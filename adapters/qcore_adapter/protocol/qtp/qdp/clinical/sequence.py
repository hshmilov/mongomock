from construct import Struct, Int32ul

CSI_SEQUENCE_NUMBER = 'csi_sequence_number'

QcoreSequence = Struct(
    'csi_sequence_timestamp' / Int32ul,
    CSI_SEQUENCE_NUMBER / Int32ul)
