import logging
import time

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from zscaler_adapter.consts import MAX_PAGES, MAX_RATE_LIMIT_TRY, DEVICE_PER_PAGE, DEFAULT_SLEEP


logger = logging.getLogger(f'axonius.{__name__}')


class ZscalerConnection(RESTConnection):
    """ rest client for Zscaler adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password or not self._apikey:
            raise RESTException('No username or password')

        try:
            key, time_ = self.obfuscate_api_key(self._apikey)
        except Exception as e:
            raise RESTException('Invalid api key')
        json = {
            'apiKey': key,
            'username': self._username,
            'password': self._password,
            'timestamp': time_,
        }
        self._url = self._url.replace('mobile', 'admin')
        self._post('api/v1/authenticatedSession', body_params=json)

    @staticmethod
    def _sleep_rate_limit(response):
        try:
            response = response.json()
            retry_after = response['Retry-After']
            time_, type_ = retry_after.split(' ')
            if type_ != 'seconds':
                logger.error('Unsupported rate limit type {type_}')
                time.sleep(DEFAULT_SLEEP)
                return
            time.sleep(int(time_))
        except Exception as e:
            logger.exception(f'Failed to sleep rate limit response {e} {response}')
            time.sleep(DEFAULT_SLEEP)

    def _do_get_device_list_request(self, page):
        for try_ in range(MAX_RATE_LIMIT_TRY):
            response = self._get('webservice/api/web/device/deviceList',
                                 url_params={'page': page, 'pageSize': DEVICE_PER_PAGE},
                                 raise_for_status=False,
                                 return_response_raw=True,
                                 use_json_in_response=False)

            if response.status_code == 429:
                self._sleep_rate_limit(response)
                continue
            break
        else:
            raise RESTException(f'Failed to fetch page numer {page} because rate limit')
        return self._handle_response(response)

    def get_device_list(self):
        self._url = self._url.replace('admin', 'mobile')

        for page in range(1, MAX_PAGES):
            try:
                devices = self._do_get_device_list_request(page)
                yield from devices
                if len(devices) < DEVICE_PER_PAGE:
                    break
            except Exception as e:
                logger.exception(f'Failed to fetch page {page}')
                break
        else:
            logger.warning('device page limit reached')

    @staticmethod
    def obfuscate_api_key(apikey):
        now = int(time.time() * 1000)
        n = str(now)[-6:]
        r = str(int(n) >> 1).zfill(6)
        key = ''
        for i in range(0, len(str(n)), 1):
            key += apikey[int(str(n)[i])]
        for j in range(0, len(str(r)), 1):
            key += apikey[int(str(r)[j]) + 2]

        return (key, now)
