import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from redcloack_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class RedcloackConnection(RESTConnection):
    """ rest client for Redcloack adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/redcloak', domain='https://api.secureworks.com/',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._permanent_headers['Authorization'] = f'APIKEY {self._username}:{self._password}'

    def _connect(self):
        self._get('hosts',
                  url_params={'offset': 0, 'count': DEVICE_PER_PAGE})

    def get_device_list(self):
        offset = 0
        while offset < MAX_NUMBER_OF_DEVICES:
            try:
                response = self._get('hosts',
                                     url_params={'offset': offset, 'count': DEVICE_PER_PAGE})
                if not response:
                    break
                yield from response['hosts']
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Bad offset {offset}')
                break
