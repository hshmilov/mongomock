import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cycognito_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class CycognitoConnection(RESTConnection):
    """ rest client for Cycognito adapter """

    def __init__(self, *args, realm, **kwargs):
        super().__init__(*args, url_base_prefix=f'v0/{realm}',
                         headers={'Content-Type': 'application/frdy+json',
                                  'Accept': 'application/frdy+json'},
                         **kwargs)
        self._realm = realm

    def _connect(self):
        if not self._apikey or not self._realm:
            raise RESTException('No username Realm or API Key')
        self._post(f'assets/ip',
                   url_params={'key': self._apikey,
                               'count': DEVICE_PER_PAGE,
                               'offset': 0},
                   body_params=[])

    def get_device_list(self):
        offset = 0
        response = self._post(f'assets/ip',
                              url_params={'key': self._apikey,
                                          'count': DEVICE_PER_PAGE,
                                          'offset': offset},
                              body_params=[])
        yield from response
        offset += DEVICE_PER_PAGE
        while offset < MAX_NUMBER_OF_DEVICES:
            try:
                response = self._post(f'assets/ip',
                                      url_params={'key': self._apikey,
                                                  'count': DEVICE_PER_PAGE,
                                                  'offset': offset},
                                      body_params=[])
                if not response or len(response) < DEVICE_PER_PAGE:
                    break
                yield from response
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                break
