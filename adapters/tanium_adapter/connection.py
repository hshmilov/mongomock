import json
import time
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from tanium_adapter.consts import MAX_DEVICES_COUNT,\
    CACHE_EXPIRATION, PAGE_SIZE_GET, SLEEP_GET, ENDPOINT_TYPE


logger = logging.getLogger(f'axonius.{__name__}')


class TaniumConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json, text/plain, */*',
                                  'User-Agent': 'axonius/tanium_adapter'},
                         **kwargs)

    def _connect(self):
        self._test_reachability()
        self._login()

    def _login(self):
        body_params = {'username': self._username, 'password': self._password}
        response = self._post('api/v2/session/login', body_params=body_params)
        if not response.get('data') or not response['data'].get('session'):
            raise RESTException(f'Bad login response: {response}')
        self._session_headers['session'] = response['data']['session']

    def _test_reachability(self):
        # get the tanium version, could be used as connectivity test as it's not an auth/api call
        response = self._get('config/console.json')
        version = response.get('serverVersion')
        if not version:
            raise RESTException(f'Bad server with no version')
        self._platform_version = version
        logger.debug(f'Running version: {self._platform_version!r}')

    def _get_endpoints(self):
        """Get all endpoints that have ever registered with Tanium using paging."""
        cache_id = 0
        page = 1
        row_start = 0
        fetched = 0

        while row_start < MAX_DEVICES_COUNT:
            try:
                options = dict()
                options['row_start'] = row_start
                options['row_count'] = PAGE_SIZE_GET
                options['cache_expiration'] = CACHE_EXPIRATION
                if cache_id:
                    options['cache_id'] = cache_id
                data = self._tanium_get('system_status', options=options)

                cache = data.pop()  # cache info should be last item
                data.pop()  # stats entry should be second to last item, we don't need it

                cache_id = cache['cache_id']
                total = cache['cache_row_count']
                fetched += len(data)
                yield from data

                if not data:
                    msg = f'PAGE #{page}: DONE no rows returned'
                    logger.debug(msg)
                    break

                if fetched >= total:
                    msg = f'PAGE #{page}: DONE hit rows total'
                    logger.debug(msg)
                    break

                row_start += PAGE_SIZE_GET
                page += 1
                time.sleep(SLEEP_GET)
            except Exception:
                logger.exception(f'Problem in the fetch, row is {row_start}')
                break

    def _tanium_get(self, endpoint, options=None):
        url = 'api/v2/' + endpoint
        response = self._get(url, extra_headers={'tanium-options': json.dumps(options or {})})
        if not response.get('data'):
            raise RESTException(f'Bad response with no data for endpoint {endpoint}')
        return response['data']

    def get_device_list(self):
        for device_raw in self._get_endpoints():
            yield device_raw, ENDPOINT_TYPE
