import logging
import time

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

    def _get(self, *args, **kwargs):
        try:
            return super()._get(*args, **kwargs)
        except Exception as e:
            if 'too many requests' in str(e).lower() or '429' in str(e):
                # The Cloudflare API sets a maximum of 1,200 requests in a five minute period.
                time.sleep(60 * 5)
                return super()._get(*args, **kwargs)
            raise

    def _connect(self):
        if not self._username or not self._apikey:
            raise RESTException('No username or password')
        try:
            # First, we try api key
            self._permanent_headers['X-Auth-Email'] = self._username
            self._permanent_headers['X-Auth-Key'] = self._apikey
            # We only need to list zones to see if we have permissions
            self._get('zones',
                      url_params={'page': 1,
                                  'per_page': DEVICE_PER_PAGE})
            return
        except Exception:
            pass

        # If that did not work lets try using api token and not api key
        self._permanent_headers.pop('X-Auth-Email', None)
        self._permanent_headers.pop('X-Auth-Key', None)
        self._permanent_headers['Authorization'] = f'Bearer {self._apikey}'

        # We need to list different endpoints to see if we have permissions.
        try:
            accounts = self._get('accounts', url_params={'page': 1})['result']
        except Exception:
            logger.exception(f'Could not query the accounts endpoint')
            raise ValueError(f'Can not connect. Please check your credentials / permissions')
        if not accounts:
            raise ValueError(f'No accounts were found. Please check API token permissions')
        for account in accounts:
            account_id = account.get('id')
            try:
                zones = self._get(f'zones', url_params={'page': 1, 'account.id': account_id})['result']
                if not zones:
                    continue
                for zone in zones:
                    zone_id = zone.get('id')
                    self._get(f'zones/{zone_id}/dns_records', url_params={'page': 1, 'per_page': 1})
                    # If we got here, it means we have permissions.
                    return
            except Exception:
                logger.exception(f'Could not get zones and records for account {account}')
        raise ValueError(f'Can not query zones / dns records. Please check API Token permissions')

    def _get_items_list(self, endpoint):
        page = 1
        response = self._get(endpoint,
                             url_params={'page': page,
                                         'per_page': DEVICE_PER_PAGE})
        yield from response['result']
        total_count = response['result_info']['total_count']
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

    # pylint: disable=too-many-nested-blocks, too-many-branches
    def get_device_list(self):
        cnamas_dict = dict()
        accounts = list(self._get_items_list('accounts'))
        for account in accounts:
            account_name = account.get('name')
            account_id = account.get('id')
            if not account_id or not account_name:
                logger.error(f'No account id or name in {accounts}, continuing.')
                continue
            zones = list(self._get_items_list(f'zones?account.id={account_id}'))
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
                            yield device_raw, cnamas_dict, (account_id, account_name)
                except Exception:
                    logger.exception(f'Problem with zone {zone}')
