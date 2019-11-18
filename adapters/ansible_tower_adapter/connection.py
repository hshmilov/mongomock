import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

from ansible_tower_adapter.consts import (
    API_HOST_URI,
    DEVICE_PER_PAGE,
    AnsibelTowerInstanceType
)

logger = logging.getLogger(f'axonius.{__name__}')


class AnsibleTowerConnection(RESTConnection):
    """ rest client for AnsibleTower adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix='api/v2',
                         headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
         # try to connect and get data

        self._get(f'{API_HOST_URI}/', url_params={'page_size': 10}, do_basic_auth=True)

    def get_device_list(self):
        """  The next and previous fields provides links to
             additional results if there are more than will fit on a single page. The
             results list contains zero or more host records.
        """
        page_indx = 1

        while page_indx != 0:
            try:

                ansibel_hosts = self._get(f'{API_HOST_URI}/',
                                          url_params={'page': page_indx, 'page_size': DEVICE_PER_PAGE},
                                          do_basic_auth=True)

                if isinstance(ansibel_hosts, dict) and ansibel_hosts:
                    for host in ansibel_hosts['results']:
                        if isinstance(host, dict) and host.get('type') == AnsibelTowerInstanceType.host.name:
                            yield host

            except Exception:
                logger.exception(msg=f'Error fetching device list')
                if page_indx == 1:
                    raise
                break

            if isinstance(ansibel_hosts, dict) and ansibel_hosts.get('next'):
                page_indx = page_indx + 1
            else:
                break
