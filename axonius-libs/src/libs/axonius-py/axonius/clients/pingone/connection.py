import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class PingoneConnection(RESTConnection):
    """ rest client for Pingone adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/directory',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')
        self._get('user', do_basic_auth=True)

    def get_user_list(self):
        yield from self._get('user', do_basic_auth=True)

    def get_device_list(self):
        pass
