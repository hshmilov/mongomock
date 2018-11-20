import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from clearpass_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES
logger = logging.getLogger(f'axonius.{__name__}')


class ClearpassConnection(RESTConnection):
    """ rest client for Clearpass adapter """

    def __init__(self, *args, client_id, client_secret, **kwargs):
        super().__init__(*args, url_base_prefix='api', headers={'Content-Type': 'application/json',
                                                                'Accept': 'application/json'}, **kwargs)
        self._client_id = client_id
        self._client_secret = client_secret

    def _connect(self):
        if self._username and self._password:
            self._post('oauth2', body_params={'grant_type': 'password',
                                              'username': self._username,
                                              'password': self._password,
                                              'client_id': self._client_id,
                                              'client_secret': self._client_secret})
            token = ''
            self._session_headers['Authorization'] = f'Bearer {token}'
        else:
            raise RESTException('No username or password')

    def get_device_list(self):
        yield from self._get_device_list_from_api('endpoint', 'endpoint')
        yield from self._get_device_list_from_api('network-device', 'network-device')

    def _get_device_list_from_api(self, api_name, device_type):
        response = self._get(api_name, url_params={'calculate_count': True,
                                                   'offset': 0, 'limit': DEVICE_PER_PAGE})
        devices_raw = response['_embedded']['items']
        for device_raw in devices_raw:
            yield device_raw, device_type
        count = response['count']
        if count >= MAX_NUMBER_OF_DEVICES:
            logger.error(f'Error, count - {count} is larger than MAX_NUMBER_OF_DEVICES '
                         f'- {MAX_NUMBER_OF_DEVICES}, skipping over pages!')
        offset = DEVICE_PER_PAGE
        while offset < min(count, MAX_NUMBER_OF_DEVICES):
            try:
                response = self._get(api_name, url_params={'calculate_count': False,
                                                           'offset': offset, 'limit': DEVICE_PER_PAGE})
                devices_raw = response['_embedded']['items']
                if not devices_raw:
                    break
                for device_raw in devices_raw:
                    yield device_raw, device_type
            except Exception:
                logger.exception(f'Problem fetching offset {offset}')
                break
