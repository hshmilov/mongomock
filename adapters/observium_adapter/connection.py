import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class ObserviumConnection(RESTConnection):
    """ rest client for Observium adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v0',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._get('devices', do_basic_auth=True)
        if not isinstance(response, dict) or not response.get('devices') \
                or not isinstance(response.get('devices'), dict):
            logger.error(f'Bad devices Resonse: {response}')
            raise RESTException(f'Invalid server response. Please check your credentials')

    def get_device_list(self):
        response = self._get('devices', do_basic_auth=True)
        if not isinstance(response, dict) or not response.get('devices') \
                or not isinstance(response.get('devices'), dict):
            logger.error(f'Bad devices Resonse: {response}')
            raise RESTException(f'Bad Devices Response')
        yield from response['devices'].values()
