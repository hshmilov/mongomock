import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from snipeit_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class SnipeitConnection(RESTConnection):
    """ rest client for Snipeit adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)
        self._permanent_headers['Authorization'] = f'Bearer {self._apikey}'

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        self._get('hardware', url_params={'limit': DEVICE_PER_PAGE, 'offset': 0})

    def get_device_list(self):
        response = self._get('hardware', url_params={'limit': DEVICE_PER_PAGE, 'offset': 0})
        yield from response['rows']
        total = response['total']
        offset = DEVICE_PER_PAGE
        while offset < min(total, MAX_NUMBER_OF_DEVICES):
            try:
                response = self._get('hardware', url_params={'limit': DEVICE_PER_PAGE, 'offset': offset})
                yield from response['rows']
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at offest {offset}')
                break
