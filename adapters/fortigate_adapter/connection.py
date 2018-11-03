import json
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from fortigate_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class FortimanagerConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        body_login = {'method': 'exec',
                      'params': [{'url': consts.LOGIN_URL,
                                  'data': {'passwd': self._password,
                                           'user': self._username},
                                  'option': None}],
                      'id': consts.EXEC_ID,
                      'verbose': False,
                      'jsonrpc': '2.0',
                      'session': 1}
        response = self._post(consts.URL_PATH, body_params=json.dumps(body_login), use_json_in_body=False)
        if 'session' not in response:
            raise RESTException(f'Bad logon got {response["result"]}')
        self._token = response['session']

    def get_device_list(self):
        for device_raw in []:
            yield device_raw, 'fortimanager_device'
