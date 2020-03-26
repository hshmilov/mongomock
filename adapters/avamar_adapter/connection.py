import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from avamar_adapter.consts import MAX_NUMBER_OF_PAGES


logger = logging.getLogger(f'axonius.{__name__}')


class AvamarConnection(RESTConnection):
    """ rest client for Avamar adapter """

    def __init__(self, *args, client_id, client_secret, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        if not client_id:
            client_id = ''
        if not client_secret:
            client_secret = ''
        self._client_id = client_id
        self._client_secret = client_secret
        self._last_refresh = None
        self._expires_in = None

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return
        grant_type = {'grant_type': 'password',
                      'username': self._username,
                      'password': self._password}
        self._session_headers['Content-Type'] = 'application/x-www-form-urlencoded'
        response = self._post('v1/oauth/swagger', body_params=grant_type,
                              use_json_in_body=False,
                              do_basic_auth=True,
                              alternative_auth_dict=(self._client_id, self._client_secret))
        if 'access_token' not in response:
            raise RESTException(f'Bad login got response: {response.content[:100]}')
        self._session_headers['Authorization'] = 'Bearer ' + response['access_token']
        self._last_refresh = datetime.datetime.now()
        self._expires_in = int(response['expires_in'])

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._last_refresh = None
        self._expires_in = None
        self._refresh_token()
        self._get('v1/clients', url_params={'page': 0})

    def get_device_list(self):
        self._refresh_token()
        page = 0
        response = self._get('v1/clients', url_params={'page': page})
        yield from response['content']
        total_pages = response['totalPages']
        page += 1
        while page < min(total_pages, MAX_NUMBER_OF_PAGES):
            try:
                response = self._get('v1/clients', url_params={'page': page})
                yield from response['content']
                page += 1
            except Exception:
                logger.exception(f'Problem with page {page}')
                break
