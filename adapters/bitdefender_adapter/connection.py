import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from bitdefender_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')

# XXX: For some reason this file doesn't ignore logging-fstring-interpolation
# although we got it in pylintrc ignore. add disable for it, and disable the disable warning
# pylint: disable=I0021
# pylint: disable=W1203


class BitdefenderConnection(RESTConnection):
    """" rest client for Bitdefender """

    def __init__(self, *args, **kwargs):
        super().__init__(url_base_prefix='api/v1.0/jsonrpc', *args, **kwargs)
        self._permanent_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        self._password = ''

    def _connect(self):
        if self._username:
            self._post('network/computers', do_basic_auth=True)
        else:
            raise RESTException('No API Key')

    def get_device_list(self):
        page_num = 1
        response = self._post('network/computers', body_params={'jsonrpc': '2.0',
                                                                'id': consts.RANDOM_REQUEST_ID,
                                                                'method': 'getEndpointsList',
                                                                'params': {'page': page_num,
                                                                           'perPage': consts.DEVICE_PER_PAGE}},
                              do_basic_auth=True)['result']['items']

        total_pages = response['result']['pagesCount']
        while page_num < total_pages and page_num < consts.MAX_PAGES_COUNT:
            page_num += 1
            try:
                yield from self._post('network/computers', do_basic_auth=True,
                                      body_params={'jsonrpc': '2.0',
                                                   'id': consts.RANDOM_REQUEST_ID,
                                                   'method': 'getEndpointsList',
                                                   'params': {'page': page_num,
                                                              'perPage': consts.DEVICE_PER_PAGE}})['result']['items']

            except Exception:
                logger.exception(f'Problem getting page number {page_num}')
