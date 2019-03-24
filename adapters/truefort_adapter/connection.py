import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class TruefortConnection(RESTConnection):
    """ rest client for Truefort adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='kotoba/rest',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('agent/all', do_basic_auth=True)

    def get_device_list(self):
        yield from self._get('agent/all', do_basic_auth=True)
