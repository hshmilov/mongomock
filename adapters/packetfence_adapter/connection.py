import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class PacketfenceConnection(RESTConnection):
    """ rest client for Packetfence adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._post('login',
                              body_params={'username': self._username,
                                           'password': self._password})
        if 'token' not in response:
            raise RESTException(f'Bad response: {response}')
        self._token = response['token']
        self._permanent_headers['Authorization'] = f'Bearer {self._token}'
        self._get('nodes')

    def get_device_list(self):
        response = self._get('nodes')
        yield from response.get('items')
        while response.get('nextCursor'):
            try:
                cursor = response.get('nextCursor')
                response = self._get('nodes', url_params={'cursor': cursor})
                yield from response.get('items')
            except Exception:
                logger.exception(f'Problem in fetch last response was {response}')
                break
