import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class GuardiumConnection(RESTConnection):
    """ rest client for Guardium adapter """

    def __init__(self, *args, client_id, client_secret, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._client_id = client_id
        self._client_secret = client_secret
        self._last_refresh = None
        self._expires_in = None

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return
        response = self._post('oauth/token',
                              use_json_in_body=False,
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                              body_params=f'client_id={self._client_id}&client_secret={self._client_secret}'
                              f'&grant_type=password&username={self._username}&password={self._password}')
        if not isinstance(response, dict) or 'access_token' not in response:
            raise RESTException(f'Bad response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._last_refresh = datetime.datetime.now()
        self._expires_in = int(response['expires_in'])

    def _connect(self):
        if not self._username or not self._password or not self._client_id or not self._client_secret:
            raise RESTException('No username or password or no Client ID/Secret')
        self._last_refresh = None
        self._expires_in = None
        self._refresh_token()
        self._get('restAPI/gim_registered_clients')

    def get_device_list(self):
        self._refresh_token()
        yield from self._get('restAPI/gim_registered_clients')
