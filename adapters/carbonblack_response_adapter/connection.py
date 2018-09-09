import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class CarbonblackResponseConnection(RESTConnection):
    def _connect(self):
        if self._username and self._password:
            self._get('auth', do_digest_auth=True)
        elif self._apikey:
            self._permanent_headers['X-Auth-Token'] = self._apikey
        else:
            raise RESTException('No user name or password')

    def get_device_list(self):
        yield from self._get('v1/sensor')
