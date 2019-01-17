import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from foreman_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class ForemanConnection(RESTConnection):
    """ rest client for Foreman adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api', headers={'Content-Type': 'application/json',
                                                                'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('hosts', url_params={'per_page': DEVICE_PER_PAGE,
                                       'page': 1},
                  do_basic_auth=True)

    def get_device_list(self):
        response = self._get('hosts', url_params={'per_page': DEVICE_PER_PAGE,
                                                  'page': 1},
                             do_basic_auth=True)
        yield from response['results']
        total = response['total']
        page = 1
        while page * DEVICE_PER_PAGE < min(total, MAX_NUMBER_OF_DEVICES):
            try:
                page += 1
                response = self._get('hosts', url_params={'per_page': DEVICE_PER_PAGE,
                                                          'page': page},
                                     do_basic_auth=True)
                yield from response['results']
            except Exception:
                logger.exception(f'Problem with offset {page}')
                break
