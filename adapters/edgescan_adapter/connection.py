import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class EdgescanConnection(RESTConnection):
    """ rest client for Edgescan adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No API Key')
        response = self._get('vulnerabilities.json', do_basic_auth=True)
        if not isinstance(response, dict) or not response.get('vulnerabilities') \
                or not isinstance(response['vulnerabilities'], list):
            raise RESTException(f'Bad Response: {response}')

    def get_device_list(self):
        yield from self._get('vulnerabilities.json', do_basic_auth=True)['vulnerabilities']
