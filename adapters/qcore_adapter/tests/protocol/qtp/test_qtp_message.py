import pytest

from qcore_adapter.protocol.qtp.common import QTP_START, QTP_END
from qcore_adapter.protocol.qtp.qtp_keepalive_message import QtpKeepAliveMessage
from qcore_adapter.protocol.qtp.qtp_message import QtpMessage
from qcore_adapter.protocol.exceptions import ProtocolException
from qcore_adapter.protocol.qtp.qtp_protocol_units import ProtocolUnit
from qcore_adapter.protocol.qtp.qdp.qdp_message_types import QdpMessageTypes


class TestQtpMessage(object):
    FIRST_MESSAGE = bytearray.fromhex('bb6732000000009c0100cc')
    CONNECTION_ESTABLISHED = bytearray.fromhex("bb6732000000009c0100cc")
    QCA_MESSAGE = bytearray.fromhex('bb6867000000000000000067669cf439ea05006700040000cc')
    KEEPALIVE = bytearray.fromhex('bbcc')
    TIME_SYNC_WITH_SIZE = bytearray.fromhex("bbdd13006704930200009c9100d85b0422000000000000cc")
    EMPTY_WITH_SIZE = bytearray(b'\xbb\xdd\x00\x00\xcc')
    FILE_DEPLOYMENT_ENQUIRY_REQUEST = bytearray.fromhex('bbdd0c0067083cbbe4119c9100000000cc')

    def test_first(self):
        m = QtpMessage()
        m.extend_bytes(self.FIRST_MESSAGE)

    def test_empty_with_len(self):
        m = QtpMessage()
        m.extend_bytes(self.EMPTY_WITH_SIZE)
        assert isinstance(m.payload_root, QtpKeepAliveMessage)

    def test_keepalive(self):
        m = QtpMessage()
        m.extend_bytes(self.KEEPALIVE)
        assert isinstance(m.payload_root, QtpKeepAliveMessage)

    def test_boundaries(self):
        m = QtpMessage()
        assert m.is_complete() is False, "Bad init"
        for byte in self.CONNECTION_ESTABLISHED[:-1]:
            m.append_byte(byte)
            assert m.is_complete() is False

        m.append_byte(self.CONNECTION_ESTABLISHED[-1])
        assert m.is_complete() is True

    def test_bad_init(self):
        m = QtpMessage()
        with pytest.raises(ProtocolException):
            m.append_byte(0x01)

    def test_append_after_done_init(self):
        m = QtpMessage()
        m.append_byte(QTP_START)
        m.append_byte(QTP_END)
        with pytest.raises(ProtocolException):
            m.append_byte(0x01)

    def test_inner_message_qdp(self):
        m = QtpMessage()
        m.extend_bytes(self.CONNECTION_ESTABLISHED)
        assert m.get_field('qtp_protocol_unit') == ProtocolUnit.QdpMessage.name
        assert m.get_field('qdp_message_type') == QdpMessageTypes.ConnectionEstablished.name

    def test_inner_message_qca(self):
        m = QtpMessage()
        m.extend_bytes(self.QCA_MESSAGE)
        assert m.get_field('qtp_protocol_unit') == ProtocolUnit.Qca.name

    def test_packet_with_len(self):
        m = QtpMessage()
        m.extend_bytes(self.TIME_SYNC_WITH_SIZE)
        assert m.get_field('client_rtc') == 570711000

    def test_file_deployment_enquiry(self):
        m = QtpMessage()
        m.extend_bytes(self.FILE_DEPLOYMENT_ENQUIRY_REQUEST)


if __name__ == '__main__':
    pytest.main([__file__])
