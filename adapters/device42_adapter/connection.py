import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from device42_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class Device42Connection(RESTConnection):
    """ rest client for Device42 adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/1.0',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('devices/all/',
                  do_basic_auth=True,
                  url_params={'limit': DEVICE_PER_PAGE,
                              'offset': 0})

    def get_device_list(self):
        offset = 0
        response = self._get('devices',
                             do_basic_auth=True,
                             url_params={'limit': DEVICE_PER_PAGE,
                                         'offset': offset})
        yield from response['Devices']
        count = response['total_count']
        offset += DEVICE_PER_PAGE
        while offset < min(count, MAX_NUMBER_OF_DEVICES):
            try:
                response = self._get('devices',
                                     do_basic_auth=True,
                                     url_params={'limit': DEVICE_PER_PAGE,
                                                 'offset': offset})
                yield from response['Devices']
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                break
