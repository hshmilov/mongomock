import pytest
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage


class TestRegistrationRequest(object):
    FILE_DEPLOYMENT_REQUEST = bytearray.fromhex('bbdd0c0067083cbbe4119c9100000000cc')

    def test_request(self):
        m = QtpMessage()
        m.extend_bytes(self.FILE_DEPLOYMENT_REQUEST)
        assert m.get_field('qdp_payload').serial == 0


if __name__ == '__main__':
    pytest.main([__file__])
