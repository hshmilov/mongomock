import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from symantec_sep_cloud_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class SymantecSepCloudConnection(RESTConnection):
    """ rest client for SymantecSepCloud adapter """

    def __init__(self, *args, domain_id, customer_id, client_id, client_secret, **kwargs):
        super().__init__(*args, url_base_prefix='/r3_epmp_i',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._domain_id = domain_id
        self._customer_id = customer_id
        self._username = client_id
        self._password = client_secret
        self._permanent_headers['x-epmp-customer-id'] = self._customer_id
        self._permanent_headers['x-epmp-domain-id'] = self._domain_id
        self._last_refresh = None
        self._expires_in = None

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return
        response = self._post('oauth2/tokens',
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                              body_params='grant_type=client_credentials',
                              use_json_in_body=False,
                              do_basic_auth=True)
        if 'access_token' not in response:
            raise RESTException(f'Bad response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._last_refresh = datetime.datetime.now()
        self._expires_in = int(response['expires_in'])

    def _connect(self):
        if not self._domain_id or not self._customer_id or not self._username or not self._password:
            raise RESTException('Missing Critical Parameter')
        self._last_refresh = None
        self._refresh_token()
        self._get('sepcloud/v1/devices',
                  url_params={'limit': DEVICE_PER_PAGE,
                              'offset': 0})

    def get_device_list(self):
        offset = 0
        while offset < MAX_NUMBER_OF_DEVICES:
            try:
                self._refresh_token()
                response = self._get('sepcloud/v1/devices',
                                     url_params={'limit': DEVICE_PER_PAGE,
                                                 'offset': offset})
                offset += DEVICE_PER_PAGE
                if not response.get('results'):
                    break
                yield from response['results']
            except Exception:
                logger.exception(f'Probelm with offset {offset}')
                break
