import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class QuestKaceConnection(RESTConnection):
    """ rest client for QuestKace adapter """

    def __init__(self, *args, orgname, **kwargs):
        self._orgname = orgname
        if not self._orgname:
            self._orgname = 'Default'
        super().__init__(*args, url_base_prefix='', headers={'Content-Type': 'application/json',
                                                             'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._post('ams/shared/api/security/login', body_params={'password': self._password,
                                                                            'userName': self._username,
                                                                            'organizationName': self._orgname},
                              use_json_in_response=False,
                              return_response_raw=True)
        if 'x-dell-csrf-token' not in response['headers']:
            raise RESTException(f'Bad Response: {response.content[:100]}')
        self._session_headers['x-dell-csrf-token'] = response['headers']['x-dell-csrf-token']

    def get_device_list(self):
        yield from self._get('api/machines?paging=limit ALL')
