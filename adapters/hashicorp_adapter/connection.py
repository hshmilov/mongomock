import logging

from axonius.clients.rest.connection import RESTConnection

logger = logging.getLogger(f'axonius.{__name__}')


class HashicorpConnection(RESTConnection):
    """ rest client for Hashicorp adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        if self._apikey:
            self._permanent_headers['Authorization'] = f'Bearer {self._apikey}'

    def _connect(self):
        self._get('catalog/nodes')

    def get_device_list(self):
        yield from self._get('catalog/nodes')
