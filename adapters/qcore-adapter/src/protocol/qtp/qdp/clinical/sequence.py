from construct import Struct, Int32ul

QcoreSequence = Struct(
    'sequence_timestamp' / Int32ul,
    'sequence_number' / Int32ul)
