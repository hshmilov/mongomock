import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class AquaConnection(RESTConnection):
    """ rest client for Aqua adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._post('v1/login',
                              body_params={'id': self._username,
                                           'password': self._password})
        if not response.get('token'):
            raise RESTException(f'Bad Token response: {response}')
        self._token = response['token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._get('v1/hosts')

    def get_device_list(self):
        yield from self._get('v1/hosts')
