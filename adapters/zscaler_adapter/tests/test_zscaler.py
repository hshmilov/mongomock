from zscaler_adapter.mock import ZscalerMockConnection
from zscaler_adapter.service import ZscalerAdapter
from test_credentials.test_zscaler_credentials import CLIENT_DETAILS

EXPECTED_RESULT = {
    'company_name': 'test company',
    'detail': 'Dell Inc. Latitude 7480',
    'device_manufacturer': 'Dell Inc.',
    'id': 'zscaler_232511',
    'last_used_users': ['test@test_company.org'],
    'network_interfaces': [{'mac': '10:65:30:49:DD:20',
                            'manufacturer': 'Dell Inc. (One Dell Way Round Rock '
                                            'TX US 78682 )'}],
    'os': {'distribution': '10', 'type': 'Windows'},
    'owner': 'test owner',
    'policy_name': 'asdf',
    'raw': {'agentVersion': '1.4.3.1',
            'companyId': 754,
            'companyName': 'test company',
            'config_download_time': '1556296829',
            'config_downloaded': 1,
            'detail': 'Dell Inc. Latitude 7480',
            'download_count': 1,
            'hardwareFingerprint': 'JC0gIFhKKiV2BB0BBANSfgN8EHMCB2JnCAQAAAAAAAA=',
            'id': 232511,
            'keepAliveTime': '1556565033',
            'macAddress': '10:65:30:49:DD:20',
            'machineHostname': '',
            'manufacturer': 'Dell Inc.',
            'osVersion': 'Windows 10 Pro',
            'owner': 'test owner',
            'policyName': 'asdf',
            'registrationState': 'Registered',
            'registration_time': '1556296829',
            'state': 1,
            'type': 3,
            'udid': '9BKBSN2:B97185CE2461C946787F73541826B23C59AAD917',
            'user': 'test@test_company.org'}}


# pylint: disable=protected-access


def test_zscaler_data():
    connection = ZscalerMockConnection(**CLIENT_DETAILS)
    connection.connect()
    devices = list(connection.get_device_list())
    assert len(devices) == 1
    device = ZscalerAdapter.MyDeviceAdapter(set(), set())
    device = ZscalerAdapter._create_device(device, devices[0])
    assert device.to_dict() == EXPECTED_RESULT
