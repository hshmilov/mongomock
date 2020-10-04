import datetime

from axonius.clients.rest.exception import RESTException
from axonius.clients.service_now.connection import ServiceNowConnection
from axonius.utils.parsing import int_or_none


class ServiceNowAkanaConnection(ServiceNowConnection):

    # NOTE - Akana gateway has no TABLE_API specific prefix
    TABLE_API_PREFIX = ''

    def __init__(self, *args, token_endpoint: str, **kwargs):
        super(ServiceNowAkanaConnection, self).__init__(*args,
                                                        url_base_prefix='digital/servicenowtablesqa/v1',
                                                        **kwargs)
        self._token_endpoint = token_endpoint
        self._session_refresh = None

    def _set_new_token(self):
        if not (self._username and self._password and self._token_endpoint):
            raise RESTException('No Akana App ID, Akana Secret or token endpoint')
        if not (isinstance(self._token_endpoint, str) and self._token_endpoint.endswith('token.oauth2')):
            raise RESTException(f'Please specify the full Token Endpoint')

        self._token_endpoint = self.build_url(self._token_endpoint, use_domain_path=True).rstrip('/')
        response = self._post(f'{self._token_endpoint}?grant_type=client_credentials&scope=api',
                              do_basic_auth=True,
                              force_full_url=True)
        if not (isinstance(response, dict) and
                response.get('access_token') and
                response.get('expires_in')):
            raise RESTException('Invalid auth response')

        self._session_headers['Authorization'] = f'Bearer {response.get("access_token")}'

        expires_in = int_or_none(response.get('expires_in'))
        if expires_in is None:
            raise RESTException(f'Auth response contains invalid expires_in')
        self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)

    def _refresh_token(self):
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            return
        self._set_new_token()

    def _connect(self):
        # all checks are performed in set_new_token
        self._set_new_token()
        self._get('cmdb_ci_computer', url_params={'sysparm_limit': 1})

    # pylint: disable=arguments-differ
    def _async_get(self, *args, **kwargs):
        """
        From docs provided for Akana integration, It appears that token can be quite short-lived.
        We inject a (potential) token refresh for every "chunk" handled.
        """
        self._refresh_token()
        return super()._async_get(*args, **kwargs)
