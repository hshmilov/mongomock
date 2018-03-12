import binascii
from construct import Struct, Pass, Int32ul, Peek, Bytes, Check, Int16ul, this

DataWithCrcHeader = Struct(
    'DataWithCrc' / Pass,
    'crc32' / Int32ul,  # make this generated if possible
    'size' / Int16ul,
    '_test_crc' / Peek(Struct(
        'data' / Bytes(this._.size),
        Check(lambda ctx: binascii.crc32(ctx.data) == ctx._.crc32)
    )),
)
