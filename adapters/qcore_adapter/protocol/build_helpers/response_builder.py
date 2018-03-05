from construct import Struct, Const, Byte, Rebuild, Int16ul, len_, this

from qcore_adapter.protocol.consts import PUMP_SERIAL, SUPPORTED_PROTOCOL_VERSION
from qcore_adapter.protocol.qtp.common import QTP_START, QTP_END, QTP_SIZE_MARKER
from qcore_adapter.protocol.qtp.qdp.qdp_log_download import LOG_RTC_TIMESTAMP, LOG_SEQUENCE_ID
from qcore_adapter.protocol.qtp.qdp.qdp_message_types import QdpMessageTypes
from qcore_adapter.protocol.qtp.qtp_decoder import QtpPayloadRoot
from qcore_adapter.protocol.qtp.qtp_protocol_units import ProtocolUnit

QtpWrapper = Struct(
    'header' / Const(QTP_START, Byte),
    'header' / Const(QTP_SIZE_MARKER, Byte),
    'len' / Rebuild(Int16ul, len_(this.data)),
    'data' / Byte[this.len],
    'trailer' / Const(QTP_END, Byte),
)


def wrap_qtp(bytes):
    return QtpWrapper.build({'data': bytes})


def wrap_qdp(msg_type, pump_serial, qdp_payload):
    qdp = {
        'qdp_message_type': msg_type,
        PUMP_SERIAL: pump_serial,
        'qdp_payload': qdp_payload,
        'protocol_version': SUPPORTED_PROTOCOL_VERSION
    }
    qtp = {'qtp_protocol_unit': ProtocolUnit.QdpMessage.name,
           'qtp_payload': qdp}
    return wrap_qtp(QtpPayloadRoot.build(qtp))


def get_registration_response_buffer(pump_serial, response=1):
    qdp_payload = {'registration_response': response}
    return wrap_qdp(QdpMessageTypes.RegistrationResponse.name, pump_serial, qdp_payload)


def get_update_settings_buffer(pump_serial, infusion_update_period_sec, tag=1):
    qdp_payload = {
        'infusion_update_period_sec': infusion_update_period_sec,
        'server_timezone': '',
        'device_id': '',
        'tag': tag
    }
    return wrap_qdp(QdpMessageTypes.DeviceUpdate.name, pump_serial, qdp_payload)


def get_log_download_message(pump_serial, ts, start, end, tag=0):
    report_start = {LOG_RTC_TIMESTAMP: ts, LOG_SEQUENCE_ID: start}
    report_end = {LOG_RTC_TIMESTAMP: ts, LOG_SEQUENCE_ID: end}

    qdp_payload = {'report_start': report_start, 'report_end': report_end, 'tag': tag}
    return wrap_qdp(QdpMessageTypes.LogDownloadRequest.name, pump_serial, qdp_payload)
