import logging
from typing import Tuple, Dict, List
from urllib.parse import urlparse

from axonius.clients.rest.connection import RESTConnection
from webscan_adapter.scanners.cert_scanner import CertScanner
from webscan_adapter.scanners.cmseek.cmseek_scanner import CMSScanner
from webscan_adapter.scanners.server_scanner import ServerScanner
from webscan_adapter.scanners.ssllabs.ssllabs_scanner import SSLLabsScanner

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

    def __init__(self, *args, fetch_ssllabs: bool, **kwargs):
        """
        Init web enrichment connection.
        :param fetch_ssllabs: should we fetch data from qualys ssllabs
        """
        self.fetch_ssllabs = fetch_ssllabs
        super().__init__(*args, **kwargs)

    def _connect(self):
        # its ok if we get an http error, we still want to get the server cert data.
        self._get('', use_json_in_response=False, raise_for_status=False)

    def get_device_list(self) -> Tuple[List, Dict]:
        """
        Get Scanners services output data
        :return: list of services, services results dict
        """
        domain = None
        try:
            domain = urlparse(self._url).netloc.split(':')[0]
        except Exception:
            logger.exception(f'Cannot parse domain: {domain}')
        logger.debug(f'scanning domain: {domain}')
        services = [ServerScanner(self._url, logger, domain, https_proxy=self._https_proxy),
                    CertScanner(self._url, logger, domain, self._port),
                    CMSScanner(self._url, logger)]
        if self.fetch_ssllabs:
            services.insert(1, SSLLabsScanner(self._url, logger, domain, https_proxy=self._https_proxy))
        results = {}
        # run scan on each service
        for service in services:
            service_name = service.__class__.__name__
            try:
                results[service_name] = service.scan()
            except Exception as e:
                logger.exception(f'Error running {service_name}: {e}')
        return services, results
