import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class DeepSecurityConnection(RESTConnection):
    """ rest client for DeepSecurity adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json', 'api-version': 'v1'},
                         **kwargs)
        self._permanent_headers['api-secret-key'] = self._apikey

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        response = self._get('computers')
        if not response.get('computers', url_params={'expand': 'none'}):
            raise RESTException(f'Bad response: {response}')

    def get_device_list(self):
        yield from self._get('computers', url_params={'expand': 'none'})['computers']
