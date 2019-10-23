import ipaddress
import logging
import re
from typing import Tuple
from urllib.parse import urlparse

import requests

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.dns import query_dns
from webscan_adapter.scanners.service_scanner import ServiceScanner

logger = logging.getLogger(f'axonius.{__name__}')


class Server(SmartJsonClass):
    name = Field(str, 'Name')
    version = Field(str, 'Version')
    full = Field(str, 'Full')


class ServerScanner(ServiceScanner):
    """
    Get http server info
    """
    QUERY_TIMEOUT = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def resolve_domain(url: str = None, domain: str = None) -> Tuple[str, str]:
        """
        Get url ot domain and resolve it.
        :param url: url to resolve its ip
        :param domain: domain to resolve
        :return: domain and ip
        """
        if not url and not domain:
            return None, None
        ip = None
        try:
            if not domain:
                domain = urlparse(url).netloc
            # if is its already an ip
            try:
                ip = str(ipaddress.ip_address(domain))
            except Exception:
                ip = query_dns(domain, timeout=ServerScanner.QUERY_TIMEOUT)
        except Exception:
            logger.exception(f'Cannot resolve {url}:{domain}')
        return domain, ip

    @staticmethod
    def parse_server_info(server: str) -> dict:
        """
        Parse server version
        :param server: server to parse
        :return: dict of name, version and full text
        """
        # get the server version - for example Apache/2.4.18 (Ubuntu)
        parsed = re.search(r'(\w*)/?([\d.]*)?', server)
        if not parsed:
            return {}
        res = parsed.groups()
        version = None
        if len(res) > 1:
            version = res[1]
        return {'name': res[0],
                'version': version,
                'full': server}

    def scan(self) -> dict:
        """
        Get cert server data form the given url / domain
        :return: server data results
        """
        # get domain ip
        domain, ip = self.resolve_domain(self.url, self.domain)
        server_data = {
            'ip': ip,
            'domain': domain
        }
        try:
            response = requests.get(self.url)
            # get HTTP headers and parse them
            headers = response.headers
            server = headers.get('Server')
            if not server:
                return {}
            server_data.update(self.parse_server_info(server))
            if headers.get('X-Powered-By'):
                server_data['powered_by'] = headers.get('X-Powered-By')
        except Exception:
            self.logger.exception('Error getting server data')
        self.results = server_data
        return self.results

    def parse(self, device: DeviceAdapter):
        """
        Parse the scan results into a DeviceAdapter data
        :param device: DeviceAdapter to add the results
        :return: None
        """
        if not self.results:
            return
        data = self.results
        if data.get('name'):
            server = Server(name=data.get('name'),
                            version=data.get('version'),
                            full=data.get('full'))
            device.server = server
        if data.get('ip'):
            device.add_nic(ips=[data.get('ip')])
        device.hostname = data.get('domain')
        # sometimes the server exposes its OS on the 'Server' header.
        device.figure_os(data.get('full'))
        device.powered_by = data.get('powered_by')
