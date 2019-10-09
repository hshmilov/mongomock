import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, JsonStringFormat, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import format_ip
from skybox_adapter.connection import SkyboxConnection
from skybox_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class SkyboxNic(SmartJsonClass):
    id = Field(str, 'ID')
    name = Field(str, 'Name')
    ip_address = Field(str, 'IP', converter=format_ip, json_format=JsonStringFormat.ip)
    description = Field(str, 'Description')
    type = Field(str, 'Type')
    zone_name = Field(str, 'Zone Name')
    zone_type = Field(str, 'Zone Type')


class SkyboxVuln(SmartJsonClass):
    comment = Field(str, 'Comment')
    cve_id = Field(str, 'CVE ID')
    description = Field(str, 'Description')
    created_by = Field(str, 'Created By')
    discovery_method = Field(str, 'Discovery Method')
    exposure = Field(str, 'Exposure')
    risk = Field(str, 'Risk')
    service_name = Field(str, 'Service Name')
    service_ports = Field(str, 'Service Ports')
    severity = Field(str, 'Severity')
    title = Field(str, 'Title')
    last_modification_time = Field(datetime.datetime, 'Last Modification Time')
    last_scan_time = Field(datetime.datetime, 'Last Scan Time')


class SkyboxAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Skybox Device Type')
        device_status = Field(str, 'Skybox Device Status')
        access_rules = Field(int, 'Skybox Access Rules')
        routing_rules = Field(int, 'Skybox Routing Rules')
        skybox_services = Field(int, 'Skybox Services')
        skybox_nics = ListField(SkyboxNic, 'Skybox Network Interfaces')
        skybox_vulnerabilities = ListField(SkyboxVuln, 'Skybox Vulnerabilities')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = SkyboxConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      https_proxy=client_config.get('https_proxy'),
                                      username=client_config['username'],
                                      password=client_config['password'])
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
        The schema SkyboxAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Skybox Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
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
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw: dict, vulnerabilities_by_host: dict):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device_id = str(device_id)
            device.id = device_id + '_' + (device_raw.get('name') or '')
            device.name = device_raw.get('name')
            device.figure_os(
                (device_raw.get('os') or '') + ' ' + (device_raw.get('osVendor') or '') + ' ' +
                (device_raw.get('osVersion') or '')
            )
            device.device_status = device_raw.get('status')
            device.device_type = device_raw.get('type')

            try:
                device.access_rules = device_raw.get('accessRules')
            except Exception:
                pass

            try:
                device.routing_rules = device_raw.get('routingRules')
            except Exception:
                pass

            try:
                device.skybox_services = device_raw.get('services')
            except Exception:
                pass

            ips = []
            try:
                for nic_raw in (device_raw.get('netInterface') or []):
                    ip_address = nic_raw.get('ipAddress')
                    if ip_address:
                        device.add_nic(ips=[ip_address], name=nic_raw.get('name'))
                        ips.append(ip_address)

                    device.skybox_nics.append(
                        SkyboxNic(
                            id=nic_raw.get('id'),
                            name=nic_raw.get('name'),
                            ip_address=nic_raw.get('ipAddress'),
                            description=nic_raw.get('description'),
                            type=nic_raw.get('type'),
                            zone_name=nic_raw.get('zoneName'),
                            zone_type=nic_raw.get('zoneType')
                        )
                    )
            except Exception:
                logger.exception(f'Problem parsing network interfaces')

            primary_ip = device_raw.get('primaryIp')
            if primary_ip and primary_ip not in ips:
                device.add_nic(ips=[primary_ip])

            try:
                vulns = vulnerabilities_by_host.get(device_id) or []
                for vuln_raw in vulns:
                    if vuln_raw.get('status') and str(vuln_raw.get('status')).lower() != 'fixed':
                        device.add_vulnerable_software(
                            cve_id=vuln_raw.get('cve'),
                            cve_description=vuln_raw.get('description')
                        )

                        device.skybox_vulnerabilities.append(
                            SkyboxVuln(
                                comment=vuln_raw.get('comment'),
                                cve_id=vuln_raw.get('cve'),
                                description=vuln_raw.get('description'),
                                created_by=vuln_raw.get('createdBy'),
                                discovery_method=vuln_raw.get('discoveryMethod'),
                                exposure=vuln_raw.get('exposure'),
                                risk=vuln_raw.get('risk'),
                                service_name=vuln_raw.get('serviceName'),
                                service_ports=vuln_raw.get('servicePorts'),
                                severity=vuln_raw.get('severity'),
                                title=vuln_raw.get('title'),
                                last_modification_time=parse_date(vuln_raw.get('lastModificationTime')),
                                last_scan_time=parse_date(vuln_raw.get('lastScanTime'))
                            )
                        )
            except Exception:
                logger.exception(f'Problem adding CVEs')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Skybox Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        devices_raw_data, vulnerabilities_by_host = devices_raw_data
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw, vulnerabilities_by_host)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
