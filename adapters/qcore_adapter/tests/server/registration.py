import pytest

from qcore_adapter.protocol.build_helpers.registration import get_registration_response_buffer
from qcore_adapter.protocol.consts import PUMP_SERIAL
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage


def test_registration():
    buff = get_registration_response_buffer(pump_serial=1337, response=1)
    parsed = QtpMessage()
    parsed.extend_bytes(bytes=buff)
    assert parsed.get_field(PUMP_SERIAL) == 1337
    assert parsed.get_field('registration_response') == 1


if __name__ == '__main__':
    pytest.main([__file__])
