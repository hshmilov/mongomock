import datetime
import logging

from funcy import chunks

from axonius.clients.rest.exception import RESTException
from axonius.clients.service_now.connection import ServiceNowConnection
from axonius.utils.parsing import int_or_none

logger = logging.getLogger(f'axonius.{__name__}')

DEFAULT_BASE_URL_PREFIX = 'digital/servicenowtablesprod/v1'


class ServiceNowAkanaConnection(ServiceNowConnection):

    # NOTE - Akana gateway has no TABLE_API specific prefix
    TABLE_API_PREFIX = ''
    USE_BASIC_AUTH = False

    def __init__(self, *args, token_endpoint: str, url_base_prefix: str, **kwargs):
        super(ServiceNowAkanaConnection, self).__init__(*args,
                                                        url_base_prefix=url_base_prefix or DEFAULT_BASE_URL_PREFIX,
                                                        **kwargs)
        self._token_endpoint = token_endpoint
        self._session_refresh = None
        self._token = None

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

        self._token = response.get('access_token')
        self._session_headers['Authorization'] = f'Bearer {self._token}'

        expires_in = int_or_none(response.get('expires_in'))
        if expires_in is None:
            raise RESTException(f'Auth response contains invalid expires_in')
        logger.info(f'Revalidated token, expires in: {expires_in}')
        if expires_in > 600:
            expires_in = expires_in - 600
        self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)

    def _refresh_token(self):
        # If session refresh will expire in 10 minutes, refresh
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            self._session_headers['Authorization'] = f'Bearer {self._token}'
            return
        self._set_new_token()

    def _connect(self):
        # all checks are performed in set_new_token
        self._set_new_token()
        self._get('cmdb_ci_computer', url_params={'sysparm_limit': 1})

    #pylint: disable=arguments-differ
    def _async_get(self, list_of_requests, *args, **kwargs):
        for higher_level_chunk in chunks(100, list_of_requests):
            self._refresh_token()
            yield from super()._async_get(higher_level_chunk, *args, **kwargs)
