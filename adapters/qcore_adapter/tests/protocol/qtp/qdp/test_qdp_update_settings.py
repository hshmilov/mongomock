import pytest
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage


# TODO: add response handling (sent in clinicalstatus2)

class TestDeviceNotify(object):
    DEVICE_UPDATE = bytearray.fromhex(
        'bbdd2a006703930200009c912c0100000e417369612f4a65727573616c656d0a515350523031363539317e150200cc')

    def test_update(self):
        m = QtpMessage()
        m.extend_bytes(self.DEVICE_UPDATE)
        assert m.get_field('qdp_payload').infusion_update_period_sec == 300


if __name__ == '__main__':
    pytest.main([__file__])
