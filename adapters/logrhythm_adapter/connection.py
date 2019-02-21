import logging

from axonius.clients.rest.connection import RESTConnection
from logrhythm_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE
logger = logging.getLogger(f'axonius.{__name__}')


class LogrhythmConnection(RESTConnection):
    """ rest client for Logrhythm adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)
        self._permanent_headers['Authorization'] = f'Bearer {self._apikey}'

    def _connect(self):
        self._get('hosts/',
                  url_params={'offset': 0,
                              'count': DEVICE_PER_PAGE})

    def get_device_list(self):
        offset = 0
        while offset < MAX_NUMBER_OF_DEVICES:
            try:
                response = self._get('hosts/',
                                     url_params={'offset': offset, 'count': DEVICE_PER_PAGE})
                if not response:
                    break
                yield from response
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                break
