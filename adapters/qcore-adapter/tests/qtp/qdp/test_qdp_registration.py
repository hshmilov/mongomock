import pytest
from protocol.qtp.qtp_decoder import QtpPayloadRoot
from protocol.qtp.qtp_message import QtpMessage
from test_helpers.qcore_fake_pump import REGISTRATION_REQUEST


class TestRegistrationRequest(object):
    RESPONSE = bytearray.fromhex('6702930200009c9101')
    ACTUAL = bytearray.fromhex(
        '67013cbbe4119c91910000000000000e001f9700000000000000000c514350333030323032383132010c8a67044e6f6e65000000002030303030303030303030303030303030303030303030303030303030303030300136044e6f6e65000000000a31342e302e333836383707302e302e302e30034c434d000000000a31342e302e3338363837013603504d4d000000000a31342e302e333836383707302e302e302e301100000000')

    def test_request(self):
        m = QtpMessage()
        m.extend_bytes(REGISTRATION_REQUEST)
        assert '14.0.1234567' in m.get_field('version', is_unique=False)
        assert m.get_field('infuser_name') == 'QCP659'

    def test_response(self):
        qdp = QtpPayloadRoot.parse(self.RESPONSE)
        assert qdp.search_all('registration_response')[0] == 1

    def test_response_actual(self):
        qdp = QtpPayloadRoot.parse(self.ACTUAL)
        assert qdp.search_all('infuser_name')[0] == 'QCP300202812'


if __name__ == '__main__':
    pytest.main([__file__])
