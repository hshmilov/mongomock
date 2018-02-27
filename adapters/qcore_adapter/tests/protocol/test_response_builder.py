import pytest

import qcore_adapter.protocol.build_helpers.response_builder as response_builder
from qcore_adapter.protocol.consts import PUMP_SERIAL
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage


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


if __name__ == '__main__':
    pytest.main([__file__])
