import logging
import ipaddress

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.adapter_exceptions import ClientConnectionException
from axonius.fields import Field, ListField
from axonius.clients.rest.connection import RESTConnection
from axonius.utils.parsing import format_mac
from axonius.smart_json_class import SmartJsonClass
from redseal_adapter.client import RedSealClient
from redseal_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


def is_ipaddr(string):
    try:
        ipaddress.ip_address(string)
    except ValueError:
        return False

    return True


PRIMARY_CAPABILITY = [
    'Firewall', 'Host',
    'Load-Balancer', 'Router',
    'Switch', 'Vpn-gateway',
    'Wireless-access-point'
]


class RedSealVulnerability(SmartJsonClass):
    scanner_name = Field(str, "Scanner Name")
    severity = Field(str, "Severity")
    cve = Field(str, "CVE")
    description = Field(str, "Vulnerability Description")
    application_name = Field(str, "Application Name")


class ArpData(SmartJsonClass):
    mac = Field(str, 'MAC Address')
    ip = Field(str, 'IP Address')
    interface = Field(str, 'Interface')


class RedsealAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        rs_primary_capability = Field(str, 'Primary Capability', enum=PRIMARY_CAPABILITY)
        rs_imported_from = Field(str, 'Imported from')
        rs_vulnerabilities = ListField(RedSealVulnerability, "Vulnerability")
        arp_data = ListField(ArpData, 'ARP Data')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return get_client_id(client_config)

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get("url"))

    def _connect_client(self, client_config):
        try:
            client = RedSealClient(**client_config)
            client.check_connection()
            return client
        except Exception as exc:
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(exc))

    def _query_devices_by_client(self, client_name, session):
        return session.get_devices(self.__async_chunks)

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "url",
                    "title": "URL",
                    "type": "string",
                    "description": "RedSeal url"
                },
                {
                    "name": "username",
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },

            ],
            "required": [
                "url",
                "username",
                "password",
            ],
            "type": "array"
        }

    def create_device(self, raw_device_data):
        kind, raw_device_data = tuple(*raw_device_data.items())

        device = self._new_device_adapter()
        if not raw_device_data.get('TreeId'):
            return None
        device.id = raw_device_data['TreeId'] + '_' + raw_device_data.get('Name')
        name = raw_device_data.get('Name')
        if name is not None and not is_ipaddr(name):
            device.hostname = name

        vendor = raw_device_data.get('OSVendor', '')

        if vendor == 'Cisco':
            device.figure_os(' '.join([vendor, str(raw_device_data.get('OSVersion', ''))]))
        else:
            device.figure_os(raw_device_data.get('OperatingSystem', ''))

        if kind.capitalize() not in PRIMARY_CAPABILITY:
            kind = raw_device_data.get('PrimaryCapability', '').capitalize()

        if kind in PRIMARY_CAPABILITY:
            device.rs_primary_capability = kind
        else:
            logger.warning(f'Unknown kind {kind}')

        for interface_dict in raw_device_data.get('Interfaces', []):
            if 'Interface' not in interface_dict:
                logger.error(f'Interface is not valid {interface_dict}')
                continue

            logger.debug(f'{interface_dict}')
            interface_list = interface_dict['Interface']

            for interface in interface_list:
                try:
                    name = interface.get('Name')
                    if is_ipaddr(name):
                        name = None

                    ip = interface.get('Address')
                    ips = [ip] if is_ipaddr(ip) else []

                    subnet = interface.get('subnet', {}).get('Name')
                    subnets = [subnet] if subnet else []

                    device.add_nic(name=name, ips=ips, subnets=subnets)
                except Exception:
                    logger.exception('Error while adding interface')

        device.rs_vulnerabilities = []
        device.software_cves = []
        for appliction_dict in raw_device_data.get('Applications', []):
            for app in appliction_dict.get('Application', []):
                for vulnerabilities in app.get('Vulnerabilities', []):
                    for vuln in vulnerabilities.get('Vulnerability', []):
                        try:
                            new_vulnerability = RedSealVulnerability()

                            new_vulnerability.application_name = app.get('Name')
                            new_vulnerability.description = vuln.get('ScannerComments') if vuln.get(
                                'Name', '') in vuln.get('ScannerComments', '') else vuln.get('Name')
                            new_vulnerability.scanner_name = vuln.get('ScannerName')
                            # Threat Reference Library
                            if 'TrlEntry' in vuln:
                                new_vulnerability.cve = vuln['TrlEntry'].get('CVE')
                                new_vulnerability.severity = vuln['TrlEntry'].get('Severity')
                                device.add_vulnerable_software(cve_id=vuln['TrlEntry'].get('CVE'))
                            device.rs_vulnerabilities.append(new_vulnerability)
                        except Exception:
                            logger.exception('Error while adding vulnerability')

        device.rs_imported_from = raw_device_data.get('ImportDevicePluginName')
        try:
            arp = ((raw_device_data.get('ARP table_full') or {}).get('Configuration') or {}).get('FileLine')
            if not isinstance(arp, list):
                arp = []
            for arp_line in arp:
                if not arp_line.get('Text'):
                    continue
                arp_text = arp_line.get('Text')
                arp_text_list = arp_text.split(' ')
                arp_text_list = [inner_text.strip() for inner_text in arp_text_list if inner_text.strip()]
                try:
                    format_mac(arp_text_list[0])
                    if not is_ipaddr(arp_text_list[1]):
                        continue
                    mac = arp_text_list[0]
                    ip = arp_text_list[1]
                    interface = None
                    if len(arp_text_list) > 2:
                        interface = arp_text_list[2]
                    device.arp_data.append(ArpData(mac=mac, ip=ip, interface=interface))
                except Exception:
                    continue
        except Exception:
            logger.exception('Problem with arp data')
        device.set_raw(raw_device_data)

        return device

    def _parse_raw_data(self, raw_data):
        if raw_data is None:
            return
        for raw_device_data in iter(raw_data):
            try:
                device = self.create_device(raw_device_data)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'async_chunks',
                    'type': 'integer',
                    'title': 'Number of requests in parallel'
                }
            ],
            'required': ['async_chunks'],
            'pretty_name': 'Redseal Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'async_chunks': 5
        }

    def _on_config_update(self, config):
        self.__async_chunks = config.get('async_chunks') or 50
