import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cloudpassage_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class CloudpassageConnection(RESTConnection):
    """ rest client for Cloudpassage adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._session_refresh = None

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('Missing key id or key secret')
        self._refresh_token()

    def _refresh_token(self):
        if self._session_refresh and self._session_refresh > datetime.datetime.now():
            return
        response = self._post('oauth/access_token',
                              url_params={'grant_type': 'client_credentials'},
                              do_basic_auth=True)
        token = response['access_token']
        expires_in = response['expires_in']
        self._session_refresh = datetime.datetime.now() + datetime.timedelta(seconds=(expires_in - 1))
        self._session_headers['Authorization'] = f'Bearer {token}'

    def get_device_list(self):
        page = 1
        self._refresh_token()
        response = self._get('v1/servers',
                             url_params={'per_page': DEVICE_PER_PAGE,
                                         'page': page})
        yield from response['servers']
        count = response['count']
        while page * DEVICE_PER_PAGE < min(MAX_NUMBER_OF_DEVICES, count):
            try:
                self._refresh_token()
                response = self._get('v1/servers',
                                     url_params={'per_page': DEVICE_PER_PAGE,
                                                 'page': page})
                if not response['servers']:
                    break
                yield from response['servers']
                page += 1
            except Exception:
                logger.exception(f'Problem at page {page}')
                break
