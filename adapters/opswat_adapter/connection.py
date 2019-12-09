import time
import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from opswat_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, MAX_RATE_LIMIT_TRY

logger = logging.getLogger(f'axonius.{__name__}')


class OpswatConnection(RESTConnection):
    """ rest client for Opswat adapter """

    def __init__(self, *args, client_id, client_secret, **kwargs):
        super().__init__(*args, url_base_prefix='o/',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._client_id = client_id
        self._client_secret = client_secret
        self._token = None
        self._token_expiration = None

    def _assure_token(self):
        if not self._token or not self._token_expiration or self._token_expiration < datetime.datetime.now():
            response = self._get('oauth/token',
                                 url_params={'client_id': self._client_id,
                                             'client_secret': self._client_secret,
                                             'grant_type': 'client_credentials'})
            self._token = response['access_token']
            self._token_expiration = datetime.datetime.now() + datetime.timedelta(seconds=response['expires_in'])

    def _connect(self):

        self._assure_token()
        self._post('api/v3.2/devices',
                   url_params={'access_token': self._token},
                   body_params={'access_token': self._token,
                                'page': 1,
                                'limit': 1})

    def _do_get_device_list_request(self, page):
        for try_ in range(MAX_RATE_LIMIT_TRY):
            response = self._post('api/v3.2/devices',
                                  url_params={'access_token': self._token},
                                  body_params={'page': page,
                                               'limit': DEVICE_PER_PAGE},
                                  raise_for_status=False,
                                  return_response_raw=True,
                                  use_json_in_response=False)

            if response.status_code == 429:
                time.sleep(60)
                continue
            break
        else:
            raise RESTException(f'Failed to fetch page numer {page} because rate limit')
        return self._handle_response(response)

    def get_device_list(self):
        page = 1
        self._assure_token()
        response = self._do_get_device_list_request(page)
        if not response:
            return
        yield from response
        while page * DEVICE_PER_PAGE < MAX_NUMBER_OF_DEVICES:
            try:
                page += 1
                self._assure_token()
                response = self._do_get_device_list_request(page)
                if not response:
                    return
                yield from response
            except Exception:
                logger.exception(f'Problem at page {page}')
                break
