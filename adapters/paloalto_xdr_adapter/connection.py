from datetime import datetime, timezone
import secrets
import logging
import hashlib
# pylint: disable=deprecated-module
import string
# pylint: enable=deprecated-module

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from paloalto_xdr_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class PaloaltoXdrConnection(RESTConnection):
    """ rest client for PaloaltoXdr adapter """

    def __init__(self, *args, api_key_id, url_base_path, **kwargs):
        if url_base_path:
            url_base_prefix = f'{url_base_path}/public_api/v1'
        else:
            url_base_prefix = 'public_api/v1'
        super().__init__(*args, url_base_prefix=url_base_prefix,
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
        self._post('endpoints/get_endpoint/', body_params={'request_data': {'filters': [{'field': 'first_seen',
                                                                                         'operator': 'gte',
                                                                                         'value': 0}],
                                                                            'search_from': 0,
                                                                            'search_to': DEVICE_PER_PAGE}})

    def get_device_list(self):
        search_from = 0
        self._update_headers()
        response = self._post('endpoints/get_endpoint/',
                              body_params={'request_data': {'filters': [{'field': 'first_seen',
                                                                         'operator': 'gte',
                                                                         'value': 0}],
                                                            'search_from': search_from,
                                                            'search_to': search_from + DEVICE_PER_PAGE}})['reply']
        yield from response['endpoints']
        search_from += DEVICE_PER_PAGE
        count = response['result_count']
        while search_from < min(count, MAX_NUMBER_OF_DEVICES):
            try:
                response = self._post('endpoints/get_endpoint/',
                                      body_params={'request_data': {'filters': [{'field': 'first_seen',
                                                                                 'operator': 'gte',
                                                                                 'value': 0}],
                                                                    'search_from': search_from,
                                                                    'search_to': search_from + DEVICE_PER_PAGE}})
                yield from response['reply']['endpoints']
                if not response['reply']['endpoints']:
                    break
                search_from += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem with offset {search_from}')
                break
