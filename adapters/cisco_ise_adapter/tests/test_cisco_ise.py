from cisco_ise_adapter.connection import CiscoIseConnection
from cisco_ise_adapter.service import CiscoIseAdapter

# pylint: disable=super-init-not-called,abstract-method,line-too-long,arguments-differ,protected-access
NETWORK_DATA = {
    'error': '',
    'response': {
        '@description': 'This is the Default Profile. Please Duplicate and save the copy. DO NOT RENAME THIS TEMPLATE.',
        '@id': 'e56f3b80-fc68-11e7-aee2-005056942907',
        '@name': '1_NETWORK_DEFAULT_DEVICE',
        '@xmlns': {
            'ers': 'ers.ise.cisco.com',
            'ns4': 'network.ers.ise.cisco.com',
            'xs': 'http://www.w3.org/2001/XMLSchema',
        },
        'NetworkDeviceGroupList': [
            {
                'NetworkDeviceGroup': [
                    'Datacenter Switch Access#Not Applicable',
                    'Device Admin#Admin Access Protocol#TACACS',
                    'Device Status#Device Status#PROD',
                    'Device Type#All Device Types#Switch',
                    'Dot1X_Mode#Implementation_Mode#Monitor',
                    'Health_Probe#Radius_Health_Probe#True',
                    'Location#All Locations#Branches',
                    'OEAP#Office Extend AP#FALSE',
                ]
            }
        ],
        'NetworkDeviceIPList': [{'NetworkDeviceIP': {'ipaddress': '1.1.1.1', 'mask': '32'}}],
        'authenticationSettings': {
            'dtlsRequired': 'false',
            'enableKeyWrap': 'false',
            'enableMultiSecret': 'false',
            'keyInputFormat': 'ASCII',
            'networkProtocol': 'RADIUS',
            'radiusSharedSecret': 'test',
        },
        'coaPort': '1700',
        'link': {
            '@href': 'https://snisepanq01s.stifelnet.stifel.local:9060/ers/config/networkdevice/e56f3b80-fc68-11e7-aee2-005056942907',
            '@rel': 'self',
            '@type': 'application/xml',
        },
        'profileName': 'Cisco',
        'snmpsettings': {
            'linkTrapQuery': 'true',
            'macTrapQuery': 'true',
            'originatingPolicyServicesNode': 'Auto',
            'pollingInterval': '28800',
            'roCommunity': 'test',
            'version': 'TWO_C',
        },
        'tacacsSettings': {
            'connectModeOptions': 'OFF',
            'previousSharedSecret': 'test',
            'previousSharedSecretExpiry': '0',
            'sharedSecret': 'test',
        },
    },
    'success': True,
}

ENDPOINT_DATA = {
    'error': '',
    'response': {
        '@id': 'd4ca54a0-0202-11e8-aee2-005056942907',
        '@name': '00:00:0C:07:AC:02',
        '@xmlns': {
            'ers': 'ers.ise.cisco.com',
            'xs': 'http://www.w3.org/2001/XMLSchema',
            'ns4': 'identity.ers.ise.cisco.com',
        },
        'link': {
            '@rel': 'self',
            '@href': 'https://snisepanq01s.stifelnet.stifel.local:9060/ers/config/endpoint/d4ca54a0-0202-11e8-aee2-005056942907',
            '@type': 'application/xml',
        },
        'groupId': 'c375dc20-222e-11e6-99ab-005056bf55e0',
        'identityStore': None,
        'identityStoreId': None,
        'mac': '00:00:0C:07:AC:02',
        'portalUser': None,
        'profileId': '250b8ca0-222f-11e6-99ab-005056bf55e0',
        'staticGroupAssignment': 'false',
        'staticProfileAssignment': 'false',
    },
    'success': True
}


class CiscoIseMockAdapter(CiscoIseAdapter):
    def __init__(self):
        pass

    def _new_device_adapter(self):
        return CiscoIseAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def get_connection(client_config):
        return CiscoIseMockConnection()


class CiscoIseMockConnection(CiscoIseConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(domain='https://tests', username='test', password='test')

    def _connect(self):
        pass

    def get_devices(self, page):
        return {'success': True, 'response': [('1_NETWORK_DEFAULT_DEVICE', 'e56f3b80-fc68-11e7-aee2-005056942907')]}

    def get_device(self, device_id):
        return NETWORK_DATA

    def get_endpoints(self, page):
        return {'success': True, 'response': [('00:00:0C:07:AC:02', 'd4ca54a0-0202-11e8-aee2-005056942907')]}

    def get_endpoint(self, device_id):
        return ENDPOINT_DATA


def test_get_network_devices():
    adapter = CiscoIseMockAdapter()
    data = adapter._query_devices_by_client('test', adapter.get_connection(''))
    devices = list(adapter._parse_raw_data(data))
    assert len(devices) == 2
    dict_ = devices[0].to_dict()
    assert (
        dict_['description']
        == 'This is the Default Profile. Please Duplicate and save the copy. DO NOT RENAME THIS TEMPLATE.'
    )
    assert dict_['name'] == '1_NETWORK_DEFAULT_DEVICE'
    assert dict_['id'] == 'e56f3b80-fc68-11e7-aee2-005056942907'
    assert len(dict_['device_group']) == 8
    assert dict_['raw']['tacacsSettings']['sharedSecret'] == '*******'

    dict2 = devices[1].to_dict()
    assert dict2['network_interfaces'][0]['mac'] == '00:00:0C:07:AC:02'
