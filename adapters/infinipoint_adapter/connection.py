import time
import logging
import jwt


from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from infinipoint_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class InfinipointConnection(RESTConnection):
    """ rest client for Infinipoint adapter """

    def __init__(self, *args, api_key, api_secret, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json'},
                         **kwargs)
        self._api_key = api_key
        self._api_secret = api_secret.replace(r'\n', '\n')

    def _renew_token(self):
        payload = {
            'iat': int(time.time()),
            'sub': self._api_key
        }
        token = jwt.encode(payload, self._api_secret, 'ES256').decode('utf-8')
        self._session_headers['Authorization'] = f'Bearer {token}'

    def _get_page(self, page):
        query = {
            'pageSize': DEVICE_PER_PAGE,
            'page': page,
            'sortBy': [
                'host'
            ],
            'sortDirection': [
                'DESC'
            ],
            'ruleSet': {
                'condition': 'OR',
                'rules': [
                ]
            }
        }
        self._renew_token()
        response = self._post('devices', body_params=query)
        return response.get('itemsTotal'), response.get('items')

    def _connect(self):
        if not self._api_key or not self._api_secret:
            raise RESTException('No API Key or Secret')
        self._get_page(0)

    def get_device_list(self):
        page = 0
        total_count, items = self._get_page(page)
        yield from items
        logger.info(f'Got total: {total_count}')
        if not total_count:
            return
        page += 1
        while (page * DEVICE_PER_PAGE) < min(MAX_NUMBER_OF_DEVICES, total_count):
            try:
                _, items = self._get_page(page)
                yield from items
                page += 1
            except Exception:
                logger.exception(f'Problem with page {page}')
                break
