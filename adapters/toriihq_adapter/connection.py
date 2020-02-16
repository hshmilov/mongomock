import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class ToriihqConnection(RESTConnection):
    """ rest client for Toriihq adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='beta',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['Authorization'] = f'Bearer {self._apikey}'

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API key')
        self._get('users')

    def get_device_list(self):
        yield from []

    def get_user_list(self):
        yield from self._get('users')['users']
