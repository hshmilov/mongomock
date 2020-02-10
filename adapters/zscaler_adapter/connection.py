import logging
import time
import requests

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from zscaler_adapter.consts import MAX_PAGES, MAX_RATE_LIMIT_TRY, DEVICE_PER_PAGE, DEFAULT_SLEEP, USER_PER_PAGE


logger = logging.getLogger(f'axonius.{__name__}')


class ZscalerConnection(RESTConnection):
    """ rest client for Zscaler adapter """

    def __init__(self, *args, rest_apikey=None, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Accept': '*/*'},
                         **kwargs)
        self._rest_apikey = rest_apikey

    def _saml_authenticate(self):
        headers = {
            'ZS_CUSTOM_CODE': self._session.cookies['ZS_SESSION_CODE'],
            'DNT': '1',
            'referer': self._url,
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0',
            'X-Requested-With': 'XMLHttpRequest'
        }
        self._session_headers.update(headers)
        resp = self._get('zsapi/v1/sso/mobilePortal')

        url = resp['url']
        saml_resp = resp['samlResponse']
        relayState = resp['relayState']

        admin_url = self._url
        self._url = self._url.replace('admin', 'mobile')

        assert url == ''.join([self._url, 'sso.do'])
        assert not relayState

        json = {
            'providername': '',
            'SAMLResponse': saml_resp,
            'RelayState': relayState if relayState else ''
        }
        self._session = requests.Session()
        self._session_headers = {
            'referer': admin_url,
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        self._post('sso.do', url_params=json, use_json_in_response=False, return_response_raw=True)
        self._session_headers.update({'auth-token': self._session.cookies['mobile-token'][1:-1]})

    def _connect(self):
        pass

    def connect_api(self):
        if not self._username or not self._password or not self._rest_apikey:
            raise RESTException('No username or password or no API Key')
        self._url = self._url.replace('mobile', 'admin')
        try:
            key, time_ = self.obfuscate_api_key(self._rest_apikey)
        except Exception as e:
            raise RESTException('Invalid api key')

        json = {
            'apiKey': key,
            'password': self._password,
            'timestamp': time_,
            'username': self._username,
        }
        self._post('api/v1/authenticatedSession', body_params=json)

    def connect_zapi(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        self._session_headers = {}
        self._apikey = 'jj7tg80fEGao'
        try:
            key, time_ = self.obfuscate_api_key(self._apikey)
        except Exception as e:
            raise RESTException('Invalid api key')

        json = {
            'apiKey': key,
            'password': self._password,
            'timestamp': time_,
            'username': self._username,
        }
        self._url = self._url.replace('mobile', 'admin')
        self._post('zsapi/v1/authenticatedSession?includeDisplayPreferences=true', body_params=json)
        self._saml_authenticate()

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
            if int(time_) != 0:
                time.sleep(int(time_))
            else:
                time.sleep(DEFAULT_SLEEP)
        except Exception as e:
            logger.exception(f'Failed to sleep rate limit response {e} {response}')
            time.sleep(DEFAULT_SLEEP)

    def _do_get_device_list_request(self, page):
        json = {'type': [1, 3],
                'user': 0,
                'osId': 0,
                'version': '',
                'configState': [1, 0],
                'osVersion': '',
                'modelId': 0
                }
        for try_ in range(MAX_RATE_LIMIT_TRY):
            response = self._post('webservice/api/web/device/deviceList',
                                  url_params={'page': page, 'pageSize': DEVICE_PER_PAGE},
                                  body_params=json,
                                  raise_for_status=False,
                                  return_response_raw=True,
                                  use_json_in_response=False)

            if response.status_code == 429:
                self._sleep_rate_limit(response)
                continue
            if response.status_code == 401:
                self.connect_zapi()
                self._url = self._url.replace('admin', 'mobile')
                self._session_headers.update({'X-Requested-With': 'XMLHttpRequest',
                                              'Accept': 'application/json, text/javascript, */*; q=0.01',
                                              'referer': ''.join([self._url, 'index.html']),
                                              'Content-Type': 'application/json'})
                continue
            break
        else:
            raise RESTException(f'Failed to fetch page numer {page} because rate limit')
        return self._handle_response(response)

    def _do_get_user_list_request(self, page):
        for try_ in range(MAX_RATE_LIMIT_TRY):
            response = self._get('api/v1/users',
                                 url_params={'page': page, 'pageSize': USER_PER_PAGE},
                                 raise_for_status=False,
                                 return_response_raw=True,
                                 use_json_in_response=False)

            if response.status_code == 429:
                self._sleep_rate_limit(response)
                continue
            if response.status_code == 401:
                self.connect_api()
                continue
            break
        else:
            raise RESTException(f'Failed to fetch page numer {page} because rate limit')
        return self._handle_response(response)

    def get_user_list(self):
        response = self._do_get_user_list_request(1)
        yield from response
        page = 2
        while len(response) > 0:
            try:
                response = self._do_get_user_list_request(page)
                yield from response
                page += 1
            except Exception:
                logger.exception(f'Problem with page {page}')
                break

    def get_device_list(self):
        self._url = self._url.replace('admin', 'mobile')
        self._session_headers.update({'X-Requested-With': 'XMLHttpRequest',
                                      'Accept': 'application/json, text/javascript, */*; q=0.01',
                                      'referer': ''.join([self._url, 'index.html']),
                                      'Content-Type': 'application/json'})

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
    def generate_time():
        return int(time.time() * 1000)

    @classmethod
    def obfuscate_api_key(cls, apikey):
        now = cls.generate_time()
        n = str(now)[-6:]
        r = str(int(n) >> 1).zfill(6)
        key = ''
        for i in range(0, len(str(n)), 1):
            key += apikey[int(str(n)[i])]
        for j in range(0, len(str(r)), 1):
            key += apikey[int(str(r)[j]) + 2]

        return (key, now)

    @classmethod
    def deobfuscate_api_key(cls, apikey, time_):
        key = {}

        n = str(time_)[-6:]
        r = str(int(n) >> 1).zfill(6)

        for i in range(0, len(str(n)), 1):
            key[int(str(n)[i])] = apikey[i]

        for j in range(0, len(str(r)), 1):
            key[int(str(r)[j]) + 2] = apikey[6 + j]

        return key
