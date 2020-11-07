import time
import hashlib
import base64
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class RiverbedConnection(RESTConnection):
    """ rest client for Riverbed adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/',
                         headers={'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if (not self._username or not self._password) and not self._apikey:
            raise RESTException('No username or password')
        if not self._apikey:
            response = self._post('mgmt.aaa/1.0/token',
                                  body_params={'user_credentials': {'username': self._username,
                                                                    'password': self._password},
                                               'generate_refresh_token': False})
            if 'access_token' not in response:
                raise RESTException(f'Bad response: {response}')
            self._token = response['access_token']
        else:
            header_encoded = '{\"alg\":\"none\"}\n'
            header_encoded = base64.b64encode(header_encoded.encode('utf-8')).decode('utf-8')
            signature_encoded = ''
            assertion = '.'.join([header_encoded, self._apikey, signature_encoded])
            state = hashlib.md5(str(time.time()).encode('utf-8')).hexdigest()
            response = self._post('common/1.0/oauth/token',
                                  use_json_in_body=False,
                                  body_params={'grant_type': 'access_code',
                                               'assertion': assertion,
                                               'state': state})
            if 'access_token' not in response:
                raise RESTException(f'Bad response: {response}')
            self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._get('cmc.appliance_inventory/1.2/appliances')

    def get_device_list(self):
        yield from self._get('cmc.appliance_inventory/1.2/appliances')
