import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from bitdefender_adapter.consts import RANDOM_REQUEST_ID, DEVICE_PER_PAGE, MAX_PAGES_COUNT, RANDOM_REQUEST_ID_2

logger = logging.getLogger(f'axonius.{__name__}')

# XXX: For some reason this file doesn't ignore logging-fstring-interpolation
# although we got it in pylintrc ignore. add disable for it, and disable the disable warning
# pylint: disable=I0021
# pylint: disable=W1203

YIELD_TYPE_TOTAL = 'TOTAL'
YIELD_TYPE_DEVICE = 'DEVICE'


class BitdefenderConnection(RESTConnection):
    """" rest client for Bitdefender """

    def __init__(self, *args, access_url_path,  **kwargs):
        super().__init__(url_base_prefix=f'{access_url_path}/v1.0/jsonrpc',
                         headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                         password='',
                         *args, **kwargs)

    def _connect(self):
        if not self._username:
            raise RESTException('No API Key')

        page_num = 1
        for _ in self._get_page_data(page_num):
            break

    def _get_page_data(self, page_num):
        response = self._post('network', body_params={'jsonrpc': '2.0',
                                                      'id': RANDOM_REQUEST_ID,
                                                      'method': 'getEndpointsList',
                                                      'params': {'page': page_num,
                                                                 'perPage': DEVICE_PER_PAGE}},
                              do_basic_auth=True)
        if not isinstance(response, dict) or not response.get('result') \
                or not isinstance(response['result'].get('items'), list):
            raise RESTException(f'Bad Response {response}')
        devices_raw = response['result']['items']
        total_pages = response['result'].get('pagesCount') or 0
        yield total_pages, YIELD_TYPE_TOTAL
        for device_raw in devices_raw:
            try:
                device_id = device_raw.get('id')
                if not device_id:
                    logger.warning(f'Device with no ID {device_raw}')
                    continue
                device_raw['extra_data'] = self._post('network', body_params={'jsonrpc': '2.0',
                                                                              'id': RANDOM_REQUEST_ID_2,
                                                                              'method': 'getManagedEndpointDetails',
                                                                              'params': {'endpointId': device_id}},
                                                      do_basic_auth=True)
            except Exception:
                logger.exception(f'problem getting extra data for {device_raw}')
            yield device_raw, YIELD_TYPE_DEVICE

    # pylint: disable=too-many-branches
    def get_device_list(self):
        page_num = 1
        total_pages = 1
        for yield_data, yield_type in self._get_page_data(page_num):
            if yield_type == YIELD_TYPE_TOTAL:
                total_pages = yield_data
            elif yield_type == YIELD_TYPE_DEVICE:
                yield yield_data
        while page_num < min(total_pages, MAX_PAGES_COUNT):
            page_num += 1
            try:
                for yield_data, yield_type in self._get_page_data(page_num):
                    if yield_type == YIELD_TYPE_DEVICE:
                        yield yield_data
            except Exception:
                logger.exception(f'Problem getting page number {page_num}')
