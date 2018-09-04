import logging

from axonius.clients.rest.connection import RESTConnection

logger = logging.getLogger(f'axonius.{__name__}')


class SophosConnection(RESTConnection):

    def __init__(self, authorization,  *args, **kwargs):
        super().__init__(*args, use_domain_path=True, **kwargs)
        self._permanent_headers = {'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'Authorization': authorization,
                                   'x-api-key':  self._apikey}

    def _connect(self):
        self._get('migration-tool/v1/endpoints')

    def get_device_list(self):
        yield from self._get('migration-tool/v1/endpoints')['items']
