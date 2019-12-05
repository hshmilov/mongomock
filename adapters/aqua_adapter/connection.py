import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from aqua_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

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
        page = 1
        response = self._get('v1/hosts', url_params={'page': page, 'pagesize': DEVICE_PER_PAGE})
        yield from response.get('result')
        count = response['count']
        while (page * DEVICE_PER_PAGE) < min(count, MAX_NUMBER_OF_DEVICES):
            try:
                page += 1
                response = self._get('v1/hosts', url_params={'page': page, 'pagesize': DEVICE_PER_PAGE})
                if not response.get('result'):
                    break
                yield from response.get('result')
            except Exception:
                logger.exception(f'Problem with page {page}')
                break
