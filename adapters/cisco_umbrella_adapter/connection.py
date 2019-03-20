import time
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cisco_umbrella_adapter.consts import DEVICE_PER_PAGE, MAX_PAGES_NUMBER

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoUmbrellaConnection(RESTConnection):
    """ rest client for CiscoUmbrella adapter """

    def __init__(self, *args, network_api_key, network_api_secret,
                 management_api_key, management_api_secret, **kwargs):
        self._network_api_key = network_api_key
        self._network_api_secret = network_api_secret
        self._management_api_key = management_api_key
        self._management_api_secret = management_api_secret
        super().__init__(*args, url_base_prefix='v1', headers={'Content-Type': 'application/json',
                                                               'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if not self._network_api_key or not self._network_api_secret \
                or not self._management_api_key or not self._management_api_secret:
            raise RESTException('Missing API keys')
        self._username = self._network_api_key
        self._password = self._network_api_secret
        self._get(f'organizations/', do_basic_auth=True)

    def get_device_list(self):
        self._username = self._network_api_key
        self._password = self._network_api_secret
        organizations = self._get(f'organizations/', do_basic_auth=True)
        self._username = self._management_api_key
        self._password = self._management_api_secret
        for org_raw in organizations:
            try:
                yield from self.get_device_list_from_org(org_raw.get('organizationId'))
            except Exception:
                logger.exception(f'Problem getting org {org_raw}')

    def get_device_list_from_org(self, org_id):
        if not org_id:
            return
        devices_raw = self._get(f'organizations/{org_id}/roamingcomputers',
                                do_basic_auth=True,
                                url_params={'page': 1,
                                            'limit': DEVICE_PER_PAGE})
        yield from devices_raw
        page = 2
        got_429 = False
        while devices_raw and page < MAX_PAGES_NUMBER:
            try:
                devices_raw = self._get(f'organizations/{org_id}/roamingcomputers',
                                        do_basic_auth=True,
                                        url_params={'page': page,
                                                    'limit': DEVICE_PER_PAGE})
                yield from devices_raw
                page += 1
                got_429 = False
            except Exception as e:
                logger.exception(f'Problem getting page {page}')
                if '429' not in str(e) or got_429:
                    break
                got_429 = True
                time.sleep(60)
