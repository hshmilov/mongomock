import datetime
import urllib.parse
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.remedy.consts import TOKEN_EXPIRATION_TIME_IN_SECONS

logger = logging.getLogger(f'axonius.{__name__}')


class RemedyConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Accept': 'application/json'}, **kwargs)
        self._last_refresh = None

    def _refresh_token(self):
        if self._last_refresh and \
                self._last_refresh + \
                datetime.timedelta(seconds=TOKEN_EXPIRATION_TIME_IN_SECONS) > datetime.datetime.now():
            return
        body_params = urllib.parse.urlencode({'username': self._username, 'password': self._password})
        token = self._post('jwt/login',
                           use_json_in_response=False,
                           use_json_in_body=False,
                           body_params=body_params,
                           extra_headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self._session_headers['Authorization'] = 'AR-JWT ' + token
        self._last_refresh = datetime.datetime.now()

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._last_refresh = None
        self._refresh_token()

    def get_device_list(self):
        pass

    def create_ticket(self, form_name, ticket_body):
        self._refresh_token()
        self._post(f'arsys/v1/entry/{form_name}',
                   body_params={'values': ticket_body})
