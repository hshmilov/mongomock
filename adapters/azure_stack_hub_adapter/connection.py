import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class AzureStackHubConnection(RESTConnection):
    """ rest client for AzureStackHub adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={
                             'Content-Type': 'application/json',
                             'Accept': 'application/json'
                         },
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

    def get_device_list(self):
        pass
