import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from twistlock_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE, \
    HOSTS_NAME, CONTAINERS_NAME, DEFENDERS_NAME

logger = logging.getLogger(f'axonius.{__name__}')


class TwistlockConnection(RESTConnection):
    """ rest client for Twistlock adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('containers',
                  do_basic_auth=True,
                  url_params={'offset': 0, 'limit': 1})

    def _get_device_list_by_type(self, device_type):
        offset = 0
        while offset < MAX_NUMBER_OF_DEVICES:
            try:
                response = self._get(device_type,
                                     do_basic_auth=True,
                                     url_params={'offset': offset, 'limit': DEVICE_PER_PAGE})
                if not response:
                    break
                for device_raw in response:
                    yield device_raw, device_type
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                break

    def get_device_list(self):
        yield from self._get_device_list_by_type(CONTAINERS_NAME)
        yield from self._get_device_list_by_type(HOSTS_NAME)
        yield from self._get_device_list_by_type(DEFENDERS_NAME)
