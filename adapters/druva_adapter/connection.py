import datetime
import logging
from oauthlib.oauth2 import BackendApplicationClient
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class DruvaConnection(RESTConnection):
    """ rest client for Druva adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._last_refresh = None
        self._expires_in = None

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return
        auth = HTTPBasicAuth(self._username, self._password)
        client = BackendApplicationClient(client_id=self._username)
        oauth = OAuth2Session(client=client)
        response = oauth.fetch_token(token_url=self._get_url_request('token'), auth=auth)
        if 'access_token' not in response:
            raise RESTException(f'Bad response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._last_refresh = datetime.datetime.now()
        self._expires_in = int(response['expires_in'])

    def _get_api_endpoint(self, endpoint_url, endpoint_objects):
        self._refresh_token()
        response = self._get(endpoint_url, url_params={'nextPageToken': ''})
        yield from response[endpoint_objects]
        next_page_token = response.get('nextPageToken')
        while next_page_token:
            try:
                self._refresh_token()
                response = self._get(endpoint_url, url_params={'nextPageToken': next_page_token})
                yield from response[endpoint_objects]
                next_page_token = response.get('nextPageToken')
            except Exception:
                logger.exception(f'Problem with token {next_page_token}')
                break

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No Client ID or Secret')
        self._last_refresh = None
        self._refresh_token()
        self._get('insync/endpoints/v1/devices', url_params={'nextPageToken': ''})

    def get_device_list(self):
        users_data = []
        try:
            users_data = list(self._get_api_endpoint('insync/usermanagement/v1/users', 'users'))
        except Exception:
            logger.exception('Problem getting users data')
        users_data_dict = {}
        for user_raw in users_data:
            try:
                if user_raw.get('userID'):
                    users_data_dict[user_raw.get('userID')] = user_raw
            except Exception:
                logger.exception(f'Problem with user raw {user_raw}')
        for device_raw in self._get_api_endpoint('insync/endpoints/v1/devices', 'devices'):
            yield device_raw, users_data_dict
