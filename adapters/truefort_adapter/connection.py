import time
import hmac
import hashlib
import base64
import logging


from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class TruefortConnection(RESTConnection):
    """ rest client for Truefort adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='kotoba/rest',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _update_headers(self, suffix):
        path = self._url_base_prefix + suffix
        cur_time = str(int(round(time.time() * 1000)))
        signing = hmac.new(self._secret_key.encode(), (path + cur_time).encode(), hashlib.sha1)
        str_encode = self._username + ':' + signing.hexdigest()
        myhmac = 'HMAC '.encode() + base64.b64encode(str_encode.encode())
        self._session_headers['Authorization'] = myhmac
        self._session_headers['time'] = cur_time

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        auth_data = {'userid': self._username, 'password': self._password}
        response = self._post('user/authenticate',
                              do_basic_auth=True,
                              body_params=auth_data)
        self._secret_key = response['data']['secretKey']
        self._update_headers('agent/all')
        self._get('agent/all')

    def get_device_list(self):
        self._update_headers('agent/all')
        yield from self._get('agent/all')
