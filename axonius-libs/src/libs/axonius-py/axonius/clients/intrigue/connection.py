import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class IntrigueConnection(RESTConnection):
    """ rest client for Intrigue adapter """

    def __init__(self, *args, collection_name, access_key, secret_key, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._access_key = access_key
        self._secret_key = secret_key
        self._permanent_headers['INTRIGUE_ACCESS_KEY'] = self._access_key
        self._permanent_headers['INTRIGUE_SECRET_KEY'] = self._secret_key
        self._collection_name = collection_name

    def _connect(self):
        if not (self._access_key and self._secret_key):
            raise RESTException('No access key or secret key')

        self._get(f'collections/{self._collection_name}/hosts')

    def get_device_list(self):
        yield from self._get(f'collections/{self._collection_name}/hosts')['result'].items()
