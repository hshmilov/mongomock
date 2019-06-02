import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from endgame_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class EndgameConnection(RESTConnection):
    """ rest client for Endgame adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._post('auth/login/',
                              body_params={'username': self._username,
                                           'password': self._password})
        if not response.get('metadata') or not response['metadata'].get('token'):
            raise RESTException(f'Bad login response: {response}')
        self._token = response['metadata']['token']
        self._session_headers['Authorization'] = f'JWT {self._token}'
        self._get('endpoints',
                  url_params={'page': 1,
                              'per_page': DEVICE_PER_PAGE}
                  )

    def get_device_list(self):
        page = 1
        response = self._get('endpoints',
                             url_params={'page': page,
                                         'per_page': DEVICE_PER_PAGE})
        yield from response['data']
        while page * DEVICE_PER_PAGE < MAX_NUMBER_OF_DEVICES:
            try:
                page += 1
                response = self._get('endpoints',
                                     url_params={'page': page,
                                                 'per_page': DEVICE_PER_PAGE})
                if not response.get('data'):
                    break
                yield from response['data']
                if len(response['data']) < DEVICE_PER_PAGE:
                    break
            except Exception:
                logger.exception(f'Problem at page {page}')
                break
