import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from cisco_umbrella_adapter.consts import DEVICE_PER_PAGE, MAX_PAGES_NUMBER

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoUmbrellaConnection(RESTConnection):
    """ rest client for CiscoUmbrella adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='v1', headers={'Content-Type': 'application/json',
                                                               'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if self._username and self._password:
            self._get(f'organizations/', do_basic_auth=True)
        else:
            raise RESTException('No username or password')

    def get_device_list(self):
        organizations = self._get(f'organizations/', do_basic_auth=True)
        for org_raw in organizations:
            try:
                yield from self.get_device_list_from_org(org_raw.get('organizationId'))
            except Exception:
                logger.exception(f'Problem getting org {org_raw}')

    def get_device_list_from_org(self, org_id):
        if not org_id:
            return
        devices_raw = self._get(f'organizations/{self._org_id}/roamingcomputers',
                                do_basic_auth=True,
                                url_params={'page': 1,
                                            'limit': DEVICE_PER_PAGE})
        yield from devices_raw
        page = 2
        while devices_raw and page < MAX_PAGES_NUMBER:
            try:
                devices_raw = self._get(f'organizations/{org_id}/roamingcomputers',
                                        do_basic_auth=True,
                                        url_params={'page': page,
                                                    'limit': DEVICE_PER_PAGE})
                yield from devices_raw
                page += 1
            except Exception:
                logger.exception(f'Problem getting page {page} breaking')
                break
