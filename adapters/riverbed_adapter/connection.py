import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class RiverbedConnection(RESTConnection):
    """ rest client for Riverbed adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/cmc.appliance_inventory/1.2',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('appliances',
                  do_basic_auth=True)

    def get_device_list(self):
        yield from self._get('appliances', do_basic_auth=True)
