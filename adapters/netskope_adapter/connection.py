import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from netskope_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class NetskopeConnection(RESTConnection):
    """ rest client for Netskope adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Token')
        response = self._get('clients', url_params={'skip': 0,
                                                    'limit': DEVICE_PER_PAGE,
                                                    'token': self._apikey})
        if not isinstance(response, dict) or not response.get('data') or not isinstance(response.get('data'), list):
            logger.error(f'Invalid response: {str(response)}')
            raise RESTException(f'Invalid response. Please check the credentials')

    def _yield_data_from_offset(self, offset):
        response = self._get('clients', url_params={'skip': offset,
                                                    'limit': DEVICE_PER_PAGE,
                                                    'token': self._apikey})
        if not isinstance(response, dict) or not response.get('data') or not isinstance(response.get('data'), list):
            raise RESTException(f'Bad Response For Clients Data')
        yield from response.get('data')

    def get_device_list(self):
        offset = 0
        yield from self._yield_data_from_offset(offset)
        offset += DEVICE_PER_PAGE
        while offset < MAX_NUMBER_OF_DEVICES:
            try:
                yield from self._yield_data_from_offset(offset)
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.info(f'Break at offset {offset}', exc_info=True)
                break
