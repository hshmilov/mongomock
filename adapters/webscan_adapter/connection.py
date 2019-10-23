import logging
from typing import Tuple, Dict, List

from axonius.clients.rest.connection import RESTConnection
from webscan_adapter.scanners.cert_scanner import CertScanner
from webscan_adapter.scanners.cmseek.cmseek_scanner import CMSScanner
from webscan_adapter.scanners.server_scanner import ServerScanner

logger = logging.getLogger(f'axonius.{__name__}')


class WebscanConnection(RESTConnection):
    """
    This class should handle multi services that gives websites info
    There are a lot of data we can get about website:
        - CMS info (cms name, plugins, themes, users ..)
        - Server info (apache version, php version, os version ..)
        - Shared domains on the same machine.
        - WHOIS info about the domain.
        - recursive info about detected subdomains.
        - If IP is given instead of domain, we can get ptr records and try to scan them.
    """

    def _connect(self):
        self._get('', use_json_in_response=False)

    def get_device_list(self) -> Tuple[List, Dict]:
        """
        Get Scanners services output data
        :return: list of services, services results dict
        """
        services = [ServerScanner(self._url, logger),
                    CertScanner(self._url, logger),
                    CMSScanner(self._url, logger)]
        results = {}
        # run scan on each service
        for service in services:
            service_name = service.__class__.__name__
            try:
                results[service_name] = service.scan()
            except Exception as e:
                logger.exception(f'Error running {service_name}: {e}')
        return services, results
