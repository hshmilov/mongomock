import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.bmc_atrium.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, FIELDS, QUERY

logger = logging.getLogger(f'axonius.{__name__}')


class BmcAtriumConnection(RESTConnection):
    """ rest client for BmcAtrium adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={},
                         **kwargs)

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')
        response = self._post('jwt/login', url_params={'username': self._username, 'password': self._password},
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self._session_headers['Authorization'] = f'AR-JWT {response}'
        self._get('arsys/v1.0/entry/AST:ComputerSystem',
                  url_params={'offset': 0,
                              'limit': DEVICE_PER_PAGE,
                              'q': QUERY,
                              'fields': FIELDS})

    def get_device_list(self):
        offset = 0
        while offset < MAX_NUMBER_OF_DEVICES:
            try:
                response = self._get('arsys/v1.0/entry/AST:ComputerSystem',
                                     url_params={'offset': offset,
                                                 'limit': DEVICE_PER_PAGE,
                                                 'q': QUERY,
                                                 'fields': FIELDS})
                if not isinstance(response, dict) or not response.get('entries'):
                    break
                for data_raw in response['entries']:
                    yield data_raw['values']
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'problem with offset {offset}')
                break
