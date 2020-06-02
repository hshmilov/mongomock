import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from sensu_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class SensuConnection(RESTConnection):
    """ rest client for Sensu adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('clients', url_params={'limit': DEVICE_PER_PAGE, 'offset': 0}, do_basic_auth=True)

    def get_device_list(self):
        offset = 0
        try:
            while offset < MAX_NUMBER_OF_DEVICES:
                response = self._get('clients', url_params={'limit': DEVICE_PER_PAGE, 'offset': offset},
                                     do_basic_auth=True)
                yield from response
                if not response:
                    break
                offset += DEVICE_PER_PAGE
        except Exception:
            logger.exception(f'Invalid request made while paginating devices at offset {offset}')
            if offset == 0:
                raise
