import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from guardicore_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class GuardicoreConnection(RESTConnection):
    """ rest client for Guardicore adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v3.0',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._post('authenticate',
                              body_params={'username': self._username,
                                           'password': self._password})
        if not response.get('access_token'):
            raise RESTException(f'Bad login response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._get('assets', url_params={'limit': DEVICE_PER_PAGE, 'offset': 0}).get('objects')

    def get_device_list(self):
        offset = 0
        response = self._get('assets', url_params={'limit': DEVICE_PER_PAGE, 'offset': offset})
        yield from response.get('objects')
        total_count = response.get('total_count')
        offset = DEVICE_PER_PAGE
        number_exception = 0
        while offset < min(MAX_NUMBER_OF_DEVICES, total_count):
            try:
                response = self._get('assets', url_params={'limit': DEVICE_PER_PAGE, 'offset': offset})
                if not response.get('objects'):
                    break
                yield from response.get('objects')
                number_exception = 0
            except Exception:
                logger.exception(f'Problem with offset {offset}')
                number_exception += 1
                if number_exception >= 3:
                    break
            offset += DEVICE_PER_PAGE
