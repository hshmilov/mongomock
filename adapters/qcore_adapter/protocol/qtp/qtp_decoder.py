from qcore_adapter.protocol.qtp.qca.qca_message import QcaHeader
from qcore_adapter.protocol.qtp.qtp_protocol_units import ProtocolUnit, ProtocolUnitReverseMapping
from qcore_adapter.protocol.qtp.qtp_keepalive_message import QtpKeepAliveMessage
from construct import Struct, this, Switch, Byte, Pass, Enum, Probe

from qcore_adapter.protocol.qtp.qdp.qdp_message import QdpHeader

QtpPayloadRoot = Struct(
    'QtpPayloadRoot' / Pass,
    'qtp_protocol_unit' / Enum(Byte, **ProtocolUnitReverseMapping),
    'qtp_payload' / Switch(this.qtp_protocol_unit,
                           {
                               ProtocolUnit.QdpMessage.name: QdpHeader,
                               ProtocolUnit.Qca.name: QcaHeader
                           }),
)


class QtpDecoder(object):
    @staticmethod
    def decode(qtp_payload):
        if len(qtp_payload) == 0:
            return QtpKeepAliveMessage()

        parsed = QtpPayloadRoot.parse(qtp_payload)
        return parsed
