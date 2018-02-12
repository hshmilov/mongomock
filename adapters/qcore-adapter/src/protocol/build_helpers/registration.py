from construct import Struct, Const, Byte, Rebuild, Int16ul, len_, this

from protocol.consts import PUMP_SERIAL
from protocol.qtp.common import QTP_START, QTP_END, QTP_SIZE_MARKER
from protocol.qtp.qdp.qdp_message_types import QdpMessageTypes
from protocol.qtp.qtp_decoder import QtpPayloadRoot
from protocol.qtp.qtp_protocol_units import ProtocolUnit

QtpWrapper = Struct(
    'header' / Const(QTP_START, Byte),
    'header' / Const(QTP_SIZE_MARKER, Byte),
    'len' / Rebuild(Int16ul, len_(this.data)),
    'data' / Byte[this.len],
    'trailer' / Const(QTP_END, Byte),
)


def wrap_qtp(bytes):
    return QtpWrapper.build({'data': bytes})


def get_registration_response_buffer(pump_serial, response=1):
    reg = {'registration_response': response}
    qdp = {
        'qdp_message_type': QdpMessageTypes.RegistrationResponse.name,
        PUMP_SERIAL: pump_serial,
        'qdp_payload': reg,
        'protocol_version': 145
    }

    qtp = {'qtp_protocol_unit': ProtocolUnit.QdpMessage.name,
           'qtp_payload': qdp}

    return wrap_qtp(QtpPayloadRoot.build(qtp))
