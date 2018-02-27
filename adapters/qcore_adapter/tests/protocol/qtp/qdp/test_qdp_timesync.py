import pytest
from qcore_adapter.protocol.qtp.qtp_decoder import QtpPayloadRoot


class TestTimeSync(object):
    TIMESYNC_FROM_PUMP = bytearray.fromhex('6704930200009c9100d85b0422000000000000')
    TIMESYNC_FROM_MEDIATOR = bytearray.fromhex(
        '6704930200009c910a515350523031363539310000000000db5b042203495354')

    def test_timesync_from_pump(self):
        qdp = QtpPayloadRoot.parse(self.TIMESYNC_FROM_PUMP)
        assert qdp.search_all('client_timezone')[0] == ''

    def test_timesync_from_mediator(self):
        qdp = QtpPayloadRoot.parse(self.TIMESYNC_FROM_MEDIATOR)
        qdp.search_all('server_timezone')[0] = 'IST'
        qdp.search_all('device_id')[0] = 'QSPR016591'


if __name__ == '__main__':
    pytest.main([__file__])
