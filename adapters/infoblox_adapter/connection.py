from axonius.clients.rest.connection import RESTConnection
import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.clients.rest.exception import RESTException


class InfobloxConnection(RESTConnection):

    def _connect(self):
        if self._username is not None and self._password is not None:
            self._get("zone_auth_return_as_object=1", do_basic_auth=True)
        else:
            raise RESTException("No username or password")

    def get_device_list(self):
        # These are the reasonable numbers of cidrs in networks
        networks = []
        for cidr in range(8, 28):
            try:
                networks.extend([network_raw["network"] for network_raw in
                                 self._get(f"network?network=.0/{cidr}&_return_as_object=1")["result"]])
            except Exception:
                logger.exception(f"Problem in networks with CIDR {cidr}")
        for network in networks:
            try:
                for device_raw in self._get(f"ipv4address?network={network}&_return_as_object=1")["result"]:
                    yield device_raw
            except Exception:
                logger.exception(f"Problem getting network {network}")
