import logging

from axonius.clients.rest.connection import RESTConnection
from netbox_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class NetboxConnection(RESTConnection):
    """ rest client for Netbox adapter """

    def __init__(self, *args, token=None, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        if token:
            self._permanent_headers['Authorization'] = f'Token {token}'

    def _connect(self):
        self._get('dcim/devices/',
                  url_params={'limit': DEVICE_PER_PAGE})

    def get_device_list(self):
        response = self._get('dcim/devices/',
                             url_params={'limit': DEVICE_PER_PAGE})
        yield from response.get('results')
        count = response.get('count')
        offset = DEVICE_PER_PAGE
        while offset < min(count, MAX_NUMBER_OF_DEVICES):
            try:
                response = self._get('dcim/devices/',
                                     url_params={'limit': DEVICE_PER_PAGE,
                                                 'offset': offset})
                yield from response.get('results')
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem with offset {offset}')
                break
