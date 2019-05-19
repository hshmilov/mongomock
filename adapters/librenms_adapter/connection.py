import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class LibrenmsConnection(RESTConnection):
    """ rest client for Librenms adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v0',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['X-Auth-Token'] = self._apikey

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        response = self._get('devices')
        if 'devices' not in response:
            raise RESTException(f'Bad response: {response}')

    def get_device_list(self):
        response = self._get('devices')
        if 'devices' not in response:
            raise RESTException(f'Bad response: {response}')
        yield from response['devices']
