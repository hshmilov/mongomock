import logging

from urllib.parse import quote

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from riskiq_adapter.consts import INVENTORY_SEARCH_URL, BODY_PARAM_SEARCH, MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE, \
    PAGINATION_SCROLL_DEFAULT, RISKIQ_API_URL_BASE_PREFIX

logger = logging.getLogger(f'axonius.{__name__}')


class RiskiqConnection(RESTConnection):
    """ rest client for Riskiq adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix=RISKIQ_API_URL_BASE_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No API Key or API Secret')
        try:
            self._post(INVENTORY_SEARCH_URL, url_params={'size': 1}, body_params=BODY_PARAM_SEARCH, do_basic_auth=True)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _count_inventory(self):
        response = self._post(INVENTORY_SEARCH_URL,
                              url_params={'size': 1},
                              body_params=BODY_PARAM_SEARCH,
                              do_basic_auth=True
                              )
        count = response.get('totalElements')
        if not count:
            logger.warning('Got 0 devices!')
            return 0
        if not isinstance(count, int):
            logger.error(f'Failed to get device count! Got {str(count)} instead.')
            return 0
        if count > MAX_NUMBER_OF_DEVICES:
            logger.warning(f'Total device count is {count},'
                           f' but only {MAX_NUMBER_OF_DEVICES} will be fetched.')
            count = MAX_NUMBER_OF_DEVICES
        logger.info(f'Device count to fetch: {count}')
        return count

    def _scroll_inventory(self,
                          scroll=PAGINATION_SCROLL_DEFAULT,
                          limit=DEVICE_PER_PAGE):
        url_params = {
            'size': limit,
            'mark': scroll,
        }
        total_results = self._count_inventory()
        page = 1  # Used for logging, so start at 1
        devices_fetched = 0

        while devices_fetched < total_results:
            try:
                response = self._post(INVENTORY_SEARCH_URL,
                                      url_params=url_params,
                                      body_params=BODY_PARAM_SEARCH,
                                      do_basic_auth=True)
            except RESTException as e:
                message = f'Failed to fetch devices after {devices_fetched}: {str(e)}'
                logger.exception(message)
                raise

            if not (response.get('content') and isinstance(response.get('content'), list)):
                logger.warning(f'Invalid content in response. Expected a list, got '
                               f'{type(response.get("content"))} instead.')
                break
            logger.debug(f'Yielding page {page} out of total {int(total_results/limit)} pages')

            yield from response.get('content')

            devices_fetched += len(response.get('content'))
            page += 1
            if response.get('last') is True or len(response.get('content')) < DEVICE_PER_PAGE:
                logger.info(f'Last page reached.')
                break
            if devices_fetched >= total_results:
                logger.info(f'Max devices reached.')
                break
            new_scroll = response.get('mark')
            if not new_scroll:
                logger.debug(response)
                logger.error(f'Failed to find next page. Scroll parameter is {new_scroll}, '
                             f'expected something like {url_params["mark"]}')
                break
            url_params['mark'] = quote(new_scroll, safe='')
        logger.info(f'Finished fetching devices, got {devices_fetched}')

    def get_device_list(self):
        try:
            yield from self._scroll_inventory()
        except RESTException as e:
            message = f'Failed to fetch devices for {self._username}: {str(e)}'
            raise RESTException(message)
