import logging
import datetime

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cyberark_pas_adapter.consts import API_LOGON_SUFFIX

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class CyberarkPasConnection(RESTConnection):
    """ rest client for CyberarkPas adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = None
        self._session_refresh = None

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        try:
            url_params = {
                'search': self._username
            }
            self._get_token()
            self._get('PasswordVault/api/Users', url_params=url_params)
        except Exception:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials')

    def _get_token(self):
        try:
            body_params = {
                'username': self._username,
                'password': self._password
            }

            self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=250)
            self._token = self._post(API_LOGON_SUFFIX, body_params=body_params, use_json_in_response=False,
                                     return_response_raw=False)  # type: bytes
            self._session_headers = {
                'Authorization': self._token.decode('utf-8').strip('"')
            }

        except Exception:
            raise ValueError(f'Error: Failed getting token, invalid request was made.')

    def _refresh_token(self):
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            return
        self._get_token()

    def _paginated_user_get(self):
        try:
            self._refresh_token()
            response = self._get('PasswordVault/api/Users')
            users = response.get('Users')
            if users and isinstance(users, list):
                for user in users:
                    if user.get('id'):
                        self._refresh_token()
                        yield self._get(f'PasswordVault/api/Users/{user.get("id")}')
        except Exception as err:
            logger.exception(f'Invalid request made, {str(err)}')
            raise

    def get_device_list(self):
        pass

    def get_user_list(self):
        try:
            yield from self._paginated_user_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
