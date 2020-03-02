import logging

from axonius.clients.rest.exception import RESTException
from axonius.clients.rest.connection import RESTConnection
from cloud_health_adapter.consts import ENDPOINTS_ASSETS, PAGINATION_FIELD_PAGE_NUMBERS, DEVICE_PER_PAGE, \
    CLOUD_HEALTH_DOMAIN_API

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class CloudHealthConnection(RESTConnection):
    """ rest client for CloudHealth adapter """

    def __init__(self, *args, api_key, **kwargs):
        super().__init__(*args,
                         url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._api_key = api_key

    def _update_headers(self):
        self._session_headers = {
            'Authorization': f'Bearer {self._api_key}'
        }

    def _validate_connection(self):
        # Check valid connection to the API
        try:
            # Validate connection only for AWS instance
            url_params = {
                'name': ENDPOINTS_ASSETS[0],
                'api_version': 2,
                'per_page': 1,
                'query': 'is_active=1'
            }

            self._get(f'{CLOUD_HEALTH_DOMAIN_API}/search', url_params=url_params)
        except RESTException as err:
            logger.exception(f'Failed connecting, {str(err)}')
            raise

    def _connect(self):
        if not self._api_key:
            raise RESTException('No API Key')
        self._update_headers()
        self._validate_connection()

    def _paginated_get(self, *args, **kwargs):
        url_params = kwargs.pop('url_params', {})
        url_params.setdefault(PAGINATION_FIELD_PAGE_NUMBERS, 1)

        # Perform the request per page
        while True:
            try:
                response = self._get(*args, url_params=url_params, **kwargs)
                if not response:
                    return
                yield from response
                url_params['page'] += 1
            except Exception as err:
                logger.exception(f'Invalid request made, {url_params}')
                break

    def _fetch_devices(self):
        try:
            for endpoint in ENDPOINTS_ASSETS:
                url_params = {
                    'name': endpoint,
                    'api_version': 2,
                    'per_page': DEVICE_PER_PAGE,
                    'query': 'is_active=1'
                }
                for device_raw in self._paginated_get('search', url_params=url_params):
                    yield device_raw, endpoint

        except RESTException as err:
            logger.exception(err)
            raise

    def get_device_list(self):
        yield from self._fetch_devices()
