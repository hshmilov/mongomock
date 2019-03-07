import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from code42_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class Code42Connection(RESTConnection):
    """ rest client for Code42 adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('Computer',
                  url_params={'pgSize': DEVICE_PER_PAGE,
                              'pgNum': 1},
                  do_basic_auth=True)

    def get_device_list(self):
        page_num = 1
        response = self._get('Computer',
                             url_params={'pgSize': DEVICE_PER_PAGE,
                                         'pgNum': page_num},
                             do_basic_auth=True)
        yield from response['data']['computers']
        while page_num * DEVICE_PER_PAGE < MAX_NUMBER_OF_DEVICES:
            try:
                page_num += 1
                response = self._get('Computer',
                                     url_params={'pgSize': DEVICE_PER_PAGE,
                                                 'pgNum': page_num},
                                     do_basic_auth=True)
                if not response['data'].get('computers'):
                    break
                yield from response['data']['computers']
            except Exception:
                logger.exception(f'Problem at page number {page_num}')
                break
