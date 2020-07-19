import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class AuvikConnection(RESTConnection):
    """ rest client for Auvik adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or api key')
        self._get('inventory/device/info', do_basic_auth=True)

    def _get_api_paginated(self, url):
        response = self._get(url, do_basic_auth=True)
        yield from response['data']
        while response['links'].get('next'):
            try:
                response = self._get(response['links'].get('next'), force_full_url=True, do_basic_auth=True)
                yield from response['data']
            except Exception:
                logger.exception(f'Problem in fetch')
                break

    def get_device_list(self):
        details_dict = dict()
        try:
            for device_details in self._get_api_paginated('inventory/device/detail'):
                details_dict[device_details.get('id')] = device_details.get('attributes')
        except Exception:
            logger.exception(f'Problem getting details')
        for device_raw in self._get_api_paginated('inventory/device/info'):
            device_id = device_raw.get('id')
            device_raw['device_details_raw'] = details_dict.get(device_id)
            yield device_raw
