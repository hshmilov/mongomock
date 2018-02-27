import pytest
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage


class TestDeviceNotify(object):
    DEVICE_NOTIFY = bytearray.fromhex('bbdd09006709930200009c9102cc')

    def test_notify(self):
        m = QtpMessage()
        m.extend_bytes(self.DEVICE_NOTIFY)
        assert m.get_field('qdp_payload').notification_type == 'UnrecognizedDrugLibrary'


if __name__ == '__main__':
    pytest.main([__file__])
