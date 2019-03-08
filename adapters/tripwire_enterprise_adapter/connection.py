import logging

from axonius.clients.rest.connection import RESTConnection

logger = logging.getLogger(f'axonius.{__name__}')


class TripWireEnterpriseConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json-rpc', 'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        self._get('nodes', do_basic_auth=True)

    def get_device_list(self):
        yield from self._get('nodes', do_basic_auth=True)
