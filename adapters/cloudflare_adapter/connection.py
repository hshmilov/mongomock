import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cloudflare_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class CloudflareConnection(RESTConnection):
    """ rest client for Cloudflare adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='client/v4',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['X-Auth-Email'] = self._username
        self._permanent_headers['X-Auth-Key'] = self._apikey

    def _connect(self):
        if not self._username or not self._apikey:
            raise RESTException('No username or password')
        self._get('zones',
                  url_params={'page': 1,
                              'per_page': DEVICE_PER_PAGE})

    def _get_items_list(self, endpoint):
        page = 1
        response = self._get(endpoint,
                             url_params={'page': page,
                                         'per_page': DEVICE_PER_PAGE})
        yield from response['result']
        total_count = response['total_count']
        while page * DEVICE_PER_PAGE < min(total_count, MAX_NUMBER_OF_DEVICES):
            try:
                page += 1
                response = self._get(endpoint,
                                     url_params={'page': page,
                                                 'per_page': DEVICE_PER_PAGE})
                if not response.get('result'):
                    break
                yield from response['result']
            except Exception:
                logger.exception(f'Problem at page {page}')
                break

    # pylint: disable=too-many-nested-blocks
    def get_device_list(self):
        cnamas_dict = dict()
        zones = self._get_items_list('zones')
        for zone in zones:
            try:
                zone_id = zone.get('id')
                if zone_id:
                    for device_raw in self._get_items_list(f'zones/{zone_id}/dns_records'):
                        if device_raw.get('type') == 'CNAME':
                            if device_raw.get('content') and device_raw.get('name'):
                                if device_raw.get('content') not in cnamas_dict:
                                    cnamas_dict[device_raw.get('content')] = []
                                cnamas_dict[device_raw.get('content')].append(device_raw.get('name'))
            except Exception:
                logger.exception(f'Problem with zone {zone}')

        for zone in zones:
            try:
                zone_id = zone.get('id')
                if zone_id:
                    for device_raw in self._get_items_list(f'zones/{zone_id}/dns_records'):
                        yield device_raw, cnamas_dict
            except Exception:
                logger.exception(f'Problem with zone {zone}')
