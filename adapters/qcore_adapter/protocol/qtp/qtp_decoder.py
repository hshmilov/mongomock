from qcore_adapter.protocol.qtp.qca.qca_message import QcaHeader
from qcore_adapter.protocol.qtp.qsu.qsu_message import QsuHeader
from qcore_adapter.protocol.qtp.qtp_protocol_units import ProtocolUnit, ProtocolUnitReverseMapping
from qcore_adapter.protocol.qtp.qtp_keepalive_message import QtpKeepAliveMessage
from construct import Struct, this, Switch, Byte, Pass, Enum, Probe, Default, GreedyRange, Check, len_, Computed

from qcore_adapter.protocol.qtp.qdp.qdp_message import QdpHeader

QtpPayloadRoot = Struct(
    'QtpPayloadRoot' / Pass,
    'qtp_protocol_unit' / Enum(Byte, **ProtocolUnitReverseMapping),
    'qtp_payload' / Switch(this.qtp_protocol_unit,
                           {
                               ProtocolUnit.QdpMessage.name: QdpHeader,
                               ProtocolUnit.Qca.name: QcaHeader,
                               ProtocolUnit.SoftwareUpdate.name: QsuHeader,

                               # wip
                               ProtocolUnit.SoftwareUpdate.Mediator: Computed("Not implemented yet"),
                               ProtocolUnit.SoftwareUpdate.ReservedForMsgSize: Computed("Not implemented yet"),
                               ProtocolUnit.SoftwareUpdate.DataWithCrc: Computed("Not implemented yet"),
                           }),
    'leftovers' / Default(GreedyRange(Byte), b''),
    Check(len_(this.leftovers) == 0)
)


class QtpDecoder(object):
    @staticmethod
    def decode(qtp_payload):
        if len(qtp_payload) == 0:
            return QtpKeepAliveMessage()

        parsed = QtpPayloadRoot.parse(qtp_payload)
        return parsed
