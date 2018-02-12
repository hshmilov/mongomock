import pytest

from protocol.qtp.qca.qca_message import QcaHeader
from protocol.qtp.qtp_decoder import QtpPayloadRoot


class TestQcaMessage(object):
    FIRST_QCA = bytearray.fromhex('67000000000000000067669cf439ea05006700040000')
    SECOND_QCA = bytearray.fromhex('67d552b9290000000070667736f2ec05006700010000')
    THIRD_QCA = bytearray.fromhex('67d552b92900000000706696d9a7e0050067000a0000')
    QCA_TO_REGISTER = bytearray.fromhex('68679302000000000000fc667736f2ec05006700010000')

    def test_first_qca(self):
        qca = QcaHeader.parse(self.FIRST_QCA)
        # TODO: finish tests
        pass

    def test_second_qca(self):
        qca = QcaHeader.parse(self.SECOND_QCA)
        # TODO: finish tests
        pass

    def test_third_qca(self):
        qca = QcaHeader.parse(self.THIRD_QCA)
        # TODO: finish tests
        pass

    def test_qca_to_register(self):
        qca = QtpPayloadRoot.parse(self.QCA_TO_REGISTER)
        pass


if __name__ == '__main__':
    pytest.main([__file__])
