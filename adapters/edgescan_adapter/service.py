import ipaddress
import datetime
import logging
from urllib3.util.url import parse_url

from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.fields import ListField, Field
from axonius.utils.datetime import parse_date
from edgescan_adapter.connection import EdgescanConnection
from edgescan_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class EdgescanVuln(SmartJsonClass):
    name = Field(str, 'Name')
    location = Field(str, 'Location')
    asset_name = Field(str, 'Asset Name')
    severity = Field(int, 'Severity')
    threat = Field(int, 'Threat')
    risk = Field(int, 'Risk')
    cvss_score = Field(float, 'CVSS Score')
    cvss_vector = Field(str, 'CVSS Vector')
    pci_compliance_status = Field(str, 'PCI Compliance Status')
    cves = ListField(str, 'CVEs')
    date_opened = Field(datetime.datetime, 'Date Opened')
    date_closed = Field(datetime.datetime, 'Date Closed')
    updated_at = Field(datetime.datetime, 'Updated At')
    created_at = Field(datetime.datetime, 'Create At')
    status = Field(str, 'Status')
    layer = Field(str, 'Layer')
    label = Field(str, 'Label')


class EdgescanAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        location = Field(str, 'Location')
        vulnerabilities_data = ListField(EdgescanVuln, 'Vulnerabilities')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = EdgescanConnection(domain=client_config['domain'],
                                        verify_ssl=client_config['verify_ssl'],
                                        https_proxy=client_config.get('https_proxy'),
                                        username='Axonius',
                                        password=client_config['apikey'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema EdgescanAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Edgescan Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, location, location_data):
        try:
            device = self._new_device_adapter()
            device.id = location
            try:
                str(ipaddress.ip_address(location))
                device.add_ips_and_macs(ips=location)
            except Exception:
                try:
                    device.hostname = parse_url(location).host
                except Exception:
                    logger.exception(f'Problem with hostname {location}')
            last_seen = None
            first_seen = None
            for location_raw in location_data:
                try:
                    severity = location_raw.get('severity') if isinstance(location_raw.get('severity'), int) else None
                    threat = location_raw.get('threat') if isinstance(location_raw.get('threat'), int) else None
                    risk = location_raw.get('risk') if isinstance(location_raw.get('risk'), int) else None
                    cvss_score = location_raw.get('cvss_score') \
                        if isinstance(location_raw.get('cvss_score'), float) else None
                    updated_at = parse_date(location_raw.get('updated_at'))
                    if not last_seen or (updated_at and updated_at > last_seen):
                        last_seen = updated_at
                    created_at = parse_date(location_raw.get('created_at'))
                    if not first_seen or (created_at and created_at < first_seen):
                        first_seen = created_at
                    cves = location_raw.get('cves')
                    if not isinstance(cves, list):
                        cves = []
                    for cve in cves:
                        device.add_vulnerable_software(cve_id=cve)
                    edgescan_vuln = EdgescanVuln(name=location_raw.get('name'),
                                                 asset_name=location_raw.get('asset_name'),
                                                 severity=severity,
                                                 risk=risk,
                                                 threat=threat,
                                                 cvss_score=cvss_score,
                                                 cvss_vector=location_raw.get('cvss_vector'),
                                                 date_opened=parse_date(location_raw.get('date_opened')),
                                                 date_closed=parse_date(location_raw.get('date_closed')),
                                                 pci_compliance_status=location_raw.get('pci_compliance_status'),
                                                 updated_at=updated_at,
                                                 created_at=created_at,
                                                 status=location_raw.get('status'),
                                                 layer=location_raw.get('layer'),
                                                 label=location_raw.get('label'),
                                                 location=location_raw.get('location')
                                                 )
                    device.vulnerabilities_data.append(edgescan_vuln)
                except Exception:
                    logger.exception(f'Problem with location {location_raw}')
            device.last_seen = last_seen
            device.first_seen = first_seen
            device.location = location
            device.set_raw({'location': location,
                            'location_data': location_data})
            return device
        except Exception:
            logger.exception(f'Problem with fetching Edgescan Device for {location}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        locations_dict = dict()
        for device_raw in devices_raw_data:
            if not device_raw.get('location'):
                continue
            location = device_raw.get('location')
            try:
                str(ipaddress.ip_address(location))
            except Exception:
                try:
                    location = parse_url(location).host
                except Exception:
                    logger.exception(f'Problem with location {device_raw}')
                    location = None
            if location not in locations_dict:
                locations_dict[location] = []
            locations_dict[location].append(device_raw)
        for location, location_data in locations_dict.items():
            device = self._create_device(location, location_data)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Vulnerability_Assessment]
