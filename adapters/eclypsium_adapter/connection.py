import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from eclypsium_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_PAGES

logger = logging.getLogger(f'axonius.{__name__}')


class EclypsiumConnection(RESTConnection):
    """ rest client for Eclypsium adapter """

    def __init__(self, *args, client_id, client_secret, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._client_id = client_id
        self._client_secret = client_secret
        self._last_refresh = None
        self._expires_in = None

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return
        if not self._client_id or not self._client_secret:
            raise RESTException('No client id or secret')
        response = self._post('oauth/service/token', body_params={'grant_type': 'client_credentials',
                                                                  'client_id': self._client_id,
                                                                  'client_secret': self._client_secret
                                                                  })
        if 'access_token' not in response:
            logger.exception(f'Bad login. Got this response {response}')
            raise RESTException('Bad login Credentials')
        token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {token}'
        self._last_refresh = datetime.datetime.now()
        self._expires_in = int(response['expires_in'])

    def _connect(self):
        if not self._client_id or not self._client_secret:
            raise RESTException('No Client ID/Secret')
        self._last_refresh = None
        self._expires_in = None
        self._refresh_token()
        page = 1
        self._get('hosts', url_params={'page': page, 'pageSize': DEVICE_PER_PAGE})

    def get_device_list(self):
        page = 1
        response = self._get('hosts', url_params={'page': page, 'pageSize': DEVICE_PER_PAGE})
        if not isinstance(response, dict) or not response.get('data') or not isinstance(response['data'], list):
            logger.error(f'Bad response: {response}')
            raise RESTException(f'Bad response: {response}')
        yield from response['data']
        pages_count = (response.get('meta') or {}).get('pagesCount')
        while page < min(MAX_NUMBER_OF_PAGES, pages_count):
            try:
                page += 1
                response = self._get('hosts', url_params={'page': page, 'pageSize': DEVICE_PER_PAGE})
                yield from response['data']
                if not response['data']:
                    break
            except Exception:
                logger.exception(f'Problem with page {page}')
                break
