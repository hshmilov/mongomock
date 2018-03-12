from construct import Struct, Enum, Byte, Probe, Embedded, Switch, this, Int32ul, Const, Computed

from qcore_adapter.protocol.qtp.common import enum_to_mapping, ChecksumHeader
from qcore_adapter.protocol.qtp.data_with_crc import DataWithCrcHeader
from qcore_adapter.protocol.qtp.qsu.consts import OperationalCode
from qcore_adapter.protocol.qtp.qsu.qsu_write_data_request import WriteDataRequestMessage
from qcore_adapter.protocol.qtp.qsu.qsu_write_response import WriteResponseMessage
from qcore_adapter.protocol.qtp.qtp_protocol_units import ProtocolUnit

QsuHeader = Struct(
    Embedded(ChecksumHeader),
    'operatinal_code' / Computed(lambda ctx: OperationalCode(ctx.following_message_type).name),
    '_data_with_crc' / Const(ProtocolUnit.DataWithCrc.value, Byte),
    Embedded(DataWithCrcHeader),
    'inner' / Embedded(Switch(this.operatinal_code, {
        OperationalCode.WriteDataRequest.name: WriteDataRequestMessage,
        OperationalCode.WriteResponse.name: WriteResponseMessage,
    })),
)
