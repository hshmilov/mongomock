import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class RumbleConnection(RESTConnection):
    """ rest client for Rumble adapter """

    def __init__(self, *args, org_id, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1.0',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._org_id = org_id
        self._permanent_headers['Authorization'] = f'Bearer {self._apikey}'

    def _connect(self):
        if not self._apikey or not self._org_id:
            raise RESTException('No API Key or Organization ID')
        self._get(f'export/org/{self._org_id}/assets.json?search=')

    def get_device_list(self):
        yield from self._get(f'export/org/{self._org_id}/assets.json?search=')
