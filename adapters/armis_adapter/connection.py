import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.datetime import parse_date
from armis_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class ArmisConnection(RESTConnection):
    """ rest client for Armis adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1', headers={'Accept': 'application/json'}, **kwargs)
        self._refresh_end = None

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        self._refresh_end = None
        self._refresh_token(force=True)

    def _refresh_token(self, force=False):
        if self._refresh_end and self._refresh_end > datetime.datetime.now() + datetime.timedelta(seconds=5) \
                and not force:
            return
        logger.info('Refreshing')
        self._session_headers['Content-type'] = 'application/x-www-form-urlencoded'
        self._session_headers['Authorization'] = self._apikey
        post_data = f'secret_key={self._apikey}'
        response = self._post('access_token/', use_json_in_body=False,
                              body_params=post_data)
        self._refresh_end = parse_date((response.get('data') or {}).get('expiration_utc')).replace(tzinfo=None)
        token = (response.get('data') or {}).get('access_token')
        if not token:
            raise RESTException(f'Got bad login response {response}')
        self._session_headers['Authorization'] = response['data']['access_token']

    def get_device_list(self):
        self._refresh_end = None
        offset = 0
        errors_count = 0
        while offset < MAX_NUMBER_OF_DEVICES:
            try:
                self._refresh_token()
                response = (self._get('devices/',
                                      url_params={'search': ' ',
                                                  'from': offset, 'length': DEVICE_PER_PAGE}).get('data')
                            or {}).get('data')
                if not response:
                    break
                yield from response
                offset += DEVICE_PER_PAGE
                if offset % 1000 == 0:
                    logger.info(f'Offset is {offset}')
                errors_count = 0
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                if errors_count == 3:
                    break
                errors_count += 1
                self._refresh_token(force=True)
