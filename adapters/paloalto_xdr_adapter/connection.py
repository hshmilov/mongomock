from datetime import datetime, timezone
import secrets
import logging
import hashlib
# pylint: disable=deprecated-module
import string
# pylint: enable=deprecated-module

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class PaloaltoXdrConnection(RESTConnection):
    """ rest client for PaloaltoXdr adapter """

    def __init__(self, *args, api_key_id, url_base_path, **kwargs):
        super().__init__(*args, url_base_prefix=f'{url_base_path}/public_api_request/public_api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._api_key_id = api_key_id

    def _update_headers(self):
        # Generate a 64 bytes random string
        nonce = ''.join([secrets.choice(string.ascii_letters + string.digits) for _ in range(64)])
        # Get the current timestamp as milliseconds.
        timestamp = int(datetime.now(timezone.utc).timestamp()) * 1000
        # Generate the auth key:
        auth_key = '%s%s%s' % (self._apikey, nonce, timestamp)
        # Convert to bytes object
        auth_key = auth_key.encode('utf-8')
        # Calculate sha256:
        api_key_hash = hashlib.sha256(auth_key).hexdigest()
        # Generate HTTP call headers
        self._session_headers = {
            'x-xdr-timestamp': str(timestamp),
            'x-xdr-nonce': nonce,
            'x-xdr-auth-id': str(self._api_key_id),
            'Authorization': api_key_hash
        }

    def _connect(self):
        if not self._api_key_id or not self._apikey:
            raise RESTException('No API Key ID or no API Key')
        self._update_headers()
        self._post('endpoints/get_endpoint', body_params={'filters': [], 'search_to': 10})

    def get_device_list(self):
        # if we don't use search_from, the default is 0, is we don't use search_to the default is no pagination
        self._update_headers()
        yield from self._post('endpoints/get_endpoint', body_params={'filters': []})['reply']['endpoints']
