import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.fresh_service.consts import MAX_NUMBER_OF_PAGES

logger = logging.getLogger(f'axonius.{__name__}')


class FreshServiceConnection(RESTConnection):
    """ rest client for FreshService adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        # This is the ok
        self._password = 'X'
        self._username = self._apikey

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No API Key')
        self._get('cmdb/items.json', do_basic_auth=True)

    def create_ticket(self, ticket_info):
        self._post('api/v2/tickets', body_params=ticket_info, do_basic_auth=True)

    def _get_api_endpoint(self, api_endpoint):
        page_num = 1
        while page_num < MAX_NUMBER_OF_PAGES:
            try:
                response = self._get(api_endpoint, url_params={'page': page_num}, do_basic_auth=True)
                if not response:
                    break
                yield from response
                page_num += 1
            except Exception:
                logger.exception(f'Problem with page {page_num}')
                break

    def get_device_list(self):
        for device_raw in self._get_api_endpoint('cmdb/items.json'):
            yield device_raw
