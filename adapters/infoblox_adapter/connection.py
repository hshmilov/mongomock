import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class InfobloxConnection(RESTConnection):

    def _connect(self):
        if self._username is not None and self._password is not None:
            try:
                self._get('zone_auth?_return_as_object=1', do_basic_auth=True)
            except Exception as e:
                logger.exception(f'can not log in')
                if '401 client error' in str(e).lower():
                    raise RESTException(f'401 Unauthorized - Please check your login credentials')
                else:
                    raise
        else:
            raise RESTException('No username or password')

    def get_device_list(self):
        # These are the reasonable numbers of cidrs in networks
        networks = []
        for cidr in range(8, 28):
            try:
                networks.extend([network_raw['network'] for network_raw in
                                 self._get(f'network?network~=.0/{cidr}&_return_as_object=1',
                                           do_basic_auth=True)['result']])
            except Exception:
                logger.exception(f'Problem in networks with CIDR {cidr}')
        for network in networks:
            try:
                for device_raw in self._get(f'ipv4address?network={network}&_return_as_object=1',
                                            do_basic_auth=True)['result']:
                    yield device_raw
            except Exception:
                logger.exception(f'Problem getting network {network}')
