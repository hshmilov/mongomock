import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class F5IcontrolConnection(RESTConnection):
    """ rest client for F5Icontrol adapter """

    def __init__(self, login_provider, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._login_provider = login_provider

    def _connect(self):
        if not self._username or not self._password or not self._login_provider:
            raise RESTException('No username or password')
        creds = {
            'username': self._username,
            'password': self._password,
            'loginProviderName': self._login_provider,
        }
        resp = self._post('mgmt/shared/authn/login', body_params=creds)
        token = (resp.get('token') or {}).get('token')
        if not token:
            raise RESTException(f'Unable to find token in {resp}')
        self._session_headers['X-F5-Auth-Token'] = token

        session_timeout = {
            'timeout': '36000',
        }
        self._patch(f'mgmt/shared/authz/tokens/{token}', body_params=session_timeout)

    def get_device_list(self):
        return []
