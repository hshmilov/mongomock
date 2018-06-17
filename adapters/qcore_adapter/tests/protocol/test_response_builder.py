import pytest

import qcore_adapter.protocol.build_helpers.response_builder as response_builder
from qcore_adapter.protocol.consts import PUMP_SERIAL
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage
from qcore_adapter.server.consts import dl_flow_packets


def test_registration():
    buff = response_builder.get_registration_response_buffer(pump_serial=1337, response=1)
    parsed = QtpMessage()
    parsed.extend_bytes(bytes=buff)
    assert parsed.get_field(PUMP_SERIAL) == 1337
    assert parsed.get_field('registration_response') == 1


def test_get_update_settings():
    buff = response_builder.get_update_settings_buffer(pump_serial=1337, infusion_update_period_sec=666)
    parsed = QtpMessage()
    parsed.extend_bytes(bytes=buff)
    assert parsed.get_field(PUMP_SERIAL) == 1337
    assert parsed.get_field('infusion_update_period_sec') == 666


def test_get_log_download_message():
    buff = response_builder.get_log_download_message(pump_serial=1337, ts=666, start={'high': 0, 'low': 1}, end={
        'high': 0, 'low': 1024}, tag=7)
    parsed = QtpMessage()
    parsed.extend_bytes(buff)
    payload = parsed.get_field('qdp_payload')
    assert payload['tag'] == 7


def test_replace_serial():
    new_serial = 12345
    for buff in dl_flow_packets:
        new_bytes = response_builder.replace_serial_and_wrap(buff, new_serial)
        qtp = QtpMessage()
        qtp.extend_bytes(new_bytes)
        assert qtp.get_field(PUMP_SERIAL) == new_serial


if __name__ == '__main__':
    pytest.main(['-s', __file__])
