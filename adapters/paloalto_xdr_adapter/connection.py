import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class PaloaltoXdrConnection(RESTConnection):
    """ rest client for PaloaltoXdr adapter """

    def __init__(self, *args, api_key_id, **kwargs):
        super().__init__(*args, url_base_prefix='public_api_request/public_api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._api_key_id = api_key_id
        self._permanent_headers['Authorization'] = self._apikey
        self._permanent_headers['x-xdr-auth-id'] = self._api_key_id

    def _connect(self):
        if not self._api_key_id or not self._apikey:
            raise RESTException('No API Key ID or no API Key')
        self._post('endpoints/get_endpoint', body_params={'filters': [], 'search_to': 10})

    def get_device_list(self):
        # if we don't use search_from, the default is 0, is we don't use search_to the default is no pagination
        yield from self._post('endpoints/get_endpoint', body_params={'filters': []})['reply']['endpoints']
