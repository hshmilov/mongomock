import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class CheckmarxConnection(RESTConnection):
    """ rest client for Checkmarx adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='cxrestapi',
                         headers={'Accept': 'application/json;v=1.0'},
                         **kwargs)
        self._last_refresh = None
        self._expires_in = None

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return
        response = self._post('auth/identity/connect/token',
                              use_json_in_body=False,
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                              body_params={'grant_type': 'password',
                                           'scope': 'sast_rest_api',
                                           'client_id': 'resource_owner_client',
                                           'client_secret': '014DF517-39D1-4453-B7B3-9930C563627C',
                                           'username': self._username,
                                           'password': self._password})
        if not isinstance(response, dict) or not response.get('access_token'):
            raise RESTException(f'Bad response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._last_refresh = datetime.datetime.now()
        expires_in = response.get('expires_in') or 3
        self._expires_in = int(expires_in) - 3

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('Missing critical parameter')
        self._last_refresh = None
        self._refresh_token()
        self._get('sast/engineServers')

    def get_device_list(self):
        yield from self._get('sast/engineServers')
