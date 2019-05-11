import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from armis_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class ArmisConnection(RESTConnection):
    """ rest client for Armis adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1', headers={'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        self._refresh_token()

    def _refresh_token(self):
        if not self._apikey:
            raise RESTException('No API Key')
        self._session_headers['Content-type'] = 'application/x-www-form-urlencoded'
        self._session_headers['Authorization'] = self._apikey
        post_data = f'secret_key={self._apikey}'
        response = self._post('access_token/', use_json_in_body=False,
                              body_params=post_data)
        token = (response.get('data') or {}).get('access_token')
        if not token:
            raise RESTException(f'Got bad login response {response}')
        self._session_headers['Authorization'] = response['data']['access_token']

    def get_device_list(self):
        offset = 0
        errors_count = 0
        while offset < MAX_NUMBER_OF_DEVICES:
            try:
                response = (self._get('devices/',
                                      url_params={'search': ' ',
                                                  'from': offset, 'length': DEVICE_PER_PAGE}).get('data')
                            or {}).get('data')
                if not response:
                    break
                yield from response
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                if errors_count == 3:
                    break
                errors_count += 1
                self._refresh_token()
