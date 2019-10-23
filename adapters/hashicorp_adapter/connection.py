import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class HashicorpConnection(RESTConnection):
    """ rest client for Hashicorp adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['Authorization'] = f'Bearer {self._apikey}'

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('catalog/nodes')

    def get_device_list(self):
        yield from self._get('catalog/nodes')
