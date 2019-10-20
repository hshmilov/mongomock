import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class PkwareConnection(RESTConnection):
    """ rest client for Pkware adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._apikey:
            raise RESTException('No username or password')
        self._post('su/api/v1.0/Login', url_params={'token': self._apikey})
        self._get('su/api/v1.0/TDE/Agent')

    def get_device_list(self):
        yield from self._get('su/api/v1.0/TDE/Agent')
