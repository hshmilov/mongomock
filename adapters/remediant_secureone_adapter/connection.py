import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.datetime import parse_date
from remediant_secureone_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class RemediantSecureoneConnection(RESTConnection):
    """ rest client for RemediantSecureone adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Accept': 'application/json'},
                         **kwargs)

        self._expires = None

    def _refresh_token(self):
        if self._expires \
                and self._expires > datetime.datetime.now():
            return
        body_params = {'token': self._apikey,
                       'userId': self._username}
        self._session_headers['Content-Type'] = 'application/x-www-form-urlencoded'
        response = self._post('api-keys/auth', body_params=body_params,
                              use_json_in_body=False)
        if 'token' not in response:
            raise RESTException(f'Bad login got response: {response.content[:100]}')
        self._session_headers['Authorization'] = 'Bearer ' + response['token']
        self._expires = parse_date(response.get('expires'))

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        self._expires = None
        self._refresh_token()

    def _get_basic_devices(self):
        page = 1
        response = self._get('computers', url_params={'page': page, 'limit': DEVICE_PER_PAGE},
                             use_json_in_response=False,
                             return_response_raw=True)
        for device_raw in response.json():
            if device_raw.get('id'):
                yield device_raw
        total_count = int(response.headers.get('X-Pagination-Total'))
        logger.info(f'Got totatl count: {total_count}')
        while page * DEVICE_PER_PAGE < min(MAX_NUMBER_OF_DEVICES, total_count):
            try:
                page += 1
                if page % 10 == 0:
                    logger.info(f'Got to page {page}')
                response = self._get('computers', url_params={'page': page, 'limit': DEVICE_PER_PAGE})
                for device_raw in response:
                    if device_raw.get('id'):
                        yield device_raw
            except Exception:
                logger.exception(f'Problem with page {page}')
                break

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, arguments-differ
    def get_device_list(self, fetch_full_data, chunk_size):
        if not fetch_full_data:
            yield from self._get_basic_devices()
            return
        async_reqs = []
        for device_raw in self._get_basic_devices():
            if not device_raw.get('id'):
                continue
            device_id = device_raw['id']
            last_scanned = parse_date(device_raw.get('last_scanned'))
            try:
                days_before = datetime.datetime.now().replace(tzinfo=None) - datetime.timedelta(days=60)
                if not last_scanned or last_scanned < days_before:
                    yield device_raw
                    continue
            except Exception:
                logger.exception(f'Problem with last scanned')
            async_reqs.append({'name': f'computers/{device_id}'})
        logger.info(f'Got total amount of reqs: {len(async_reqs)}')
        for i, async_response in enumerate(self._async_get(async_reqs, chunks=chunk_size)):
            if i % 100 == 0:
                logger.info(f'Got {i} devices in async')
            if self._is_async_response_good(async_response):
                yield async_response
            else:
                logger.warning(f'Bad response: {async_response}')
