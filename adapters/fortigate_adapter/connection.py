import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')

URL_PATH = 'jsonrpc'
RANDOM_ID_1 = '72'
LOGIN_URL = 'sys/login/user'


class FortimanagerConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        body_login = {'method': 'exec',
                      'params': [{'url': LOGIN_URL,
                                  'data': {'passwd': self._password,
                                           'user': self._username},
                                  'option': None}],
                      'id': RANDOM_ID_1,
                      'verbose': False,
                      'jsonrpc': '2.0',
                      'session': 1}
        response = self._post(URL_PATH, body_params=body_login)
        if 'session' not in response:
            raise RESTException(f'Bad logon got {response["result"]}')
        self._token = response['session']

    def get_device_list(self):
        for device_raw in []:
            yield device_raw, 'fortimanager_device'
