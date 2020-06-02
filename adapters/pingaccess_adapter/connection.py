import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class PingaccessConnection(RESTConnection):
    """ rest client for Pingaccess adapter """

    def __init__(self, *args, company_domain, client_id, client_secret, **kwargs):
        super().__init__(*args, url_base_prefix='', domain='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._username = client_id
        self._password = client_secret
        self._last_refresh = None
        self._expires_in = None
        self._company_domain = company_domain

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return
        response = self._post(f'https://sso.{self._company_domain}/as/token.oauth2',
                              force_full_url=True,
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                              body_params='grant_type=client_credentials&scope=read',
                              use_json_in_body=False,
                              do_basic_auth=True)
        if 'access_token' not in response:
            raise RESTException(f'Bad response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._last_refresh = datetime.datetime.now()
        self._expires_in = int(response['expires_in']) - 5

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('Missing Critical Parameter')
        self._last_refresh = None
        self._refresh_token()

    def get_user_list(self):
        try:
            self._refresh_token()
            yield from self._get(f'https://api.{self._company_domain}/v1/GetOrganizationReportWrapper',
                                 force_full_url=True)['data']
        except RESTException as err:
            logger.exception(str(err))
            raise

    def get_device_list(self):
        pass
