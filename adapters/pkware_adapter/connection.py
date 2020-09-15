import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from pkware_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES


logger = logging.getLogger(f'axonius.{__name__}')


class PkwareConnection(RESTConnection):
    """ rest client for Pkware adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='mds',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._apikey:
            raise RESTException('No username or password')
        response = self._post('su/api/v1.0/Login', url_params={'token': self._apikey})
        self._session_headers['Authorization'] = f'MDS {response}'
        self._get('su/api/v1.0/Archive/Device', url_params={'$top': DEVICE_PER_PAGE, '$skip': 0})

    def get_device_list(self):
        skip = 0
        while skip < MAX_NUMBER_OF_DEVICES:
            try:
                response = self._get('su/api/v1.0/Archive/Device', url_params={'$top': DEVICE_PER_PAGE, '$skip': skip})
                yield from response
                if len(response) < DEVICE_PER_PAGE:
                    break
                skip += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem with skip {skip}')
                break
