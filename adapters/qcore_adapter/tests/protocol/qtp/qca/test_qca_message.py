import construct
import pytest

from qcore_adapter.protocol.qtp.common import checksum256
from qcore_adapter.protocol.qtp.qca.qca_message import QcaHeader
from qcore_adapter.protocol.qtp.qtp_decoder import QtpPayloadRoot


class TestQcaMessage(object):
    def test_first_qca(self):
        buff = bytearray.fromhex('67000000000000000067669cf439ea05006700040000')
        qca = QcaHeader.parse(buff)
        assert qca.checksum == 103

    def test_checksum(self):
        buff = bytearray.fromhex('67000000000000000067669cf439ea05006700040000')
        buff[0] = 68
        with pytest.raises(construct.core.ChecksumError):
            qca = QcaHeader.parse(buff)

    def test_second_qca(self):
        qca = QcaHeader.parse(bytearray.fromhex('67d552b9290000000070667736f2ec05006700010000'))
        assert qca.checksum == 112
        pass

    def test_third_qca(self):
        qca = QcaHeader.parse(bytearray.fromhex('67d552b92900000000706696d9a7e0050067000a0000'))
        pass

    def test_qca_to_register(self):
        qca = QtpPayloadRoot.parse(bytearray.fromhex('68679302000000000000fc667736f2ec05006700010000'))
        pass


if __name__ == '__main__':
    pytest.main(['-s', __file__])
