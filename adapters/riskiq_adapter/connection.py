import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from riskiq_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class RiskiqConnection(RESTConnection):
    """ rest client for Riskiq adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _count_inventory(self):
        response = self._post('inventory/search',
                              url_params={'results': 1, 'offset': 0},
                              body_params=consts.BODY_PARAM_SEARCH,
                              do_basic_auth=True
                              )
        count = response.get('totalResults')
        if not count:
            logger.warning('Got 0 devices!')
            return 0
        if not isinstance(count, int):
            logger.error(f'Failed to get device count! Got {str(count)} instead.')
            return 0
        if count > consts.MAX_NUMBER_OF_DEVICES:
            logger.warning(f'Total device count is {count},'
                           f' but only {consts.MAX_NUMBER_OF_DEVICES} will be fetched.')
            count = consts.MAX_NUMBER_OF_DEVICES
        logger.info(f'Device count to fetch: {count}')
        return count

    def _scroll_inventory(self,
                          scroll='',
                          limit=consts.DEVICE_PER_PAGE,
                          timeout=consts.SCROLL_TIMEOUT):
        url_params = {
            'results': limit,
            'scroll': scroll,
            'timeout': timeout,
        }
        total_results = self._count_inventory()
        page = 0
        devices_fetched = 0
        try:
            response = self._post('inventory/search',
                                  url_params=url_params,
                                  body_params=consts.BODY_PARAM_SEARCH,
                                  do_basic_auth=True)
        except RESTException as e:
            message = f'Failed to fetch devices for {self._username}'
            logger.exception(message)
        else:
            while response.get('inventoryAsset'):
                if not isinstance(response.get('inventoryAsset'), list):
                    break
                logger.debug(f'Yielding page {page} out of total {int(total_results/limit)} pages')
                yield from response.get('inventoryAsset')
                devices_fetched += limit
                page += 1
                logger.debug(f'Yielded {devices_fetched} devices, out of {total_results}')
                if devices_fetched >= total_results:
                    logger.warning('Not fetching new devices, because maximum reached.')
                    break
                new_scroll = response.get('scroll')
                if not new_scroll:
                    logger.debug(response)
                    logger.error(f'Failed to find next page. Scroll parameter is {new_scroll}, '
                                 f'expected something like {url_params["scroll"]}')
                    break
                url_params['scroll'] = new_scroll
                try:
                    response = self._post('inventory/search',
                                          url_params=url_params,
                                          body_params=consts.BODY_PARAM_SEARCH,
                                          do_basic_auth=True)
                except RESTException as e:
                    message = f'Failed to get devices for page {page}: {str(e)}. ' \
                              f'Fetched total {devices_fetched} devices.'
                    logger.exception(message)
                    break

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No apikey or secret')
        self._count_inventory()

    def get_device_list(self):
        try:
            yield from self._scroll_inventory()
        except RESTException as e:
            message = f'Failed to fetch devices for {self._username}'
            logger.exception(message)
            yield {}
