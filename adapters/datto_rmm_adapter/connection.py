import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from datto_rmm_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class DattoRmmConnection(RESTConnection):
    """ rest client for DattoRmm adapter """

    def __init__(self, *args, api_secretkey, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Accept': 'application/json'},
                         **kwargs)
        self._api_secretkey = api_secretkey
        self._username = 'public-client'
        self._password = 'public'

    def _connect(self):
        if not self._apikey or not self._api_secretkey:
            raise RESTException('No API Key or Secret Key')
        self._session_headers['Content-Type'] = 'application/x-www-form-urlencoded'
        data = f'grant_type=password&username={self._apikey}&password={self._api_secretkey}'
        response = self._post('auth/oauth/token',
                              use_json_in_body=False,
                              body_params=data,
                              do_basic_auth=True)
        if 'access_token' not in response:
            raise RESTException(f'No Token in response. Respnse is {response}')
        self._session_headers['Authorization'] = 'Bearer ' + response['access_token']
        self._get('api/v2/account/devices',
                  url_params={'page': 0,
                              'max': DEVICE_PER_PAGE})

    def get_device_list(self):
        page = 0
        response = self._get('api/v2/account/devices',
                             url_params={'page': page,
                                         'max': DEVICE_PER_PAGE})
        yield from response['devices']
        page += 1
        while response.get('nextPageUrl') and page * DEVICE_PER_PAGE < MAX_NUMBER_OF_DEVICES:
            try:
                response = self._get('api/v2/account/devices',
                                     url_params={'page': page,
                                                 'max': DEVICE_PER_PAGE})
                if not response.get('devices'):
                    break
                yield from response['devices']
                page += 1
            except Exception:
                logger.exception(f'Problem with page {page}')
                break
