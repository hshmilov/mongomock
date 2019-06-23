import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.haveibeenpwned.consts import HAVEIBEENPWNED_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class HaveibeenpwnedConnection(RESTConnection):
    """ rest client for Haveibeenpwned adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v2',
                         domain=HAVEIBEENPWNED_DOMAIN,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def get_breach_account_info(self, email):
        return self._get(f'breachedaccount/{email}')

    def _connect(self):
        pass

    def get_device_list(self):
        pass
