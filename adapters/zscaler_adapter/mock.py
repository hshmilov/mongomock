import json
import requests

from zscaler_adapter.connection import ZscalerConnection

# pylint: disable=protected-access

RATE_LIMIT_RESPONE = {
    'message': 'Rate Limit (1/SECOND) exceeded',
    'Retry-After': '1 seconds'
}

DATA = [{'agentVersion': '1.4.3.1',
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
         'user': 'test@test_company.org',
         }]


class ZscalerMockConnection(ZscalerConnection):
    def __init__(self, *args, **kwargs):
        self._get_number = 0
        super().__init__(*args, **kwargs)

    def _post(self, *args, **kwargs):
        pass

    def _get(self, *args, **kwargs):
        response = requests.Response()
        if self._get_number == 0:
            response.status_code = 429
            response._content = json.dumps(RATE_LIMIT_RESPONE).encode()
        else:
            response.status_code = 200
            response._content = json.dumps(DATA).encode()
        self._get_number += 1
        return response
