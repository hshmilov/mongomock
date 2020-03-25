import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, DeviceOpenPortVulnerabilityAndFix
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from kenna_adapter import consts
from kenna_adapter.connection import KennaConnection
from kenna_adapter.client_id import get_client_id
from kenna_adapter.structures import AssetGroup

logger = logging.getLogger(f'axonius.{__name__}')


class KennaAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        asset_id = Field(int, 'Asset ID')
        asset_tags = ListField(str, 'Asset Tags')
        asset_groups = ListField(AssetGroup, 'Asset Groups')
        fqdn = Field(str, 'FQDN')
        netbios_name = Field(str, 'Netbios Name')
        external_id = Field(str, 'External ID')
        url = Field(str, 'URL')
        affected_file = Field(str, 'Affected File Path')
        database = Field(str, 'Database Name')
        status = Field(str, 'Status')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config['domain'],
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = KennaConnection(domain=client_config['domain'],
                                     api_token=client_config['api_token'],
                                     verify_ssl=client_config['verify_ssl'],
                                     https_proxy=client_config.get('https_proxy'))
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
        The schema KennaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Kenna Security Platform URL',
                    'type': 'string',
                    'default': consts.DEFAULT_DOMAIN,
                },
                {
                    'name': 'api_token',
                    'title': 'API Token',
                    'type': 'string',
                    'format': 'password',
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool',
                    'default': True,
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'api_token',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_generic_fields(device: MyDeviceAdapter, device_raw, device_vulnerabilities):
        try:
            ip_address = device_raw.get('ip_address')
            device.first_seen = parse_date(device_raw.get('created_at'))
            device.last_seen = parse_date(device_raw.get('last_seen_time'))
            device.host_name = device_raw.get('hostname') or device_raw.get('fqdn')
            device.add_ips_and_macs(ips=[ip_address, device_raw.get('ipv6')],
                                    macs=[device_raw.get('mac_address')])
            device.set_boot_time(boot_time=device_raw.get('last_booted_at'))
            network_ports = device_raw.get('network_ports')
            if not isinstance(network_ports, list):
                network_ports = [network_ports]
            for port in network_ports:
                device.add_open_port(protocol=port.get('protocol'),
                                     port_id=port.get('port_number'),
                                     service_name=port.get('product'))
                device.add_installed_software(name=port.get('product'), version=port.get('version'))
            device.figure_os(f'{device_raw.get("operating_system")}')
            device.boot_time = parse_date(device_raw.get('last_booted_at'))
            open_ports_vulns_and_fixes = []
            for vuln in device_vulnerabilities:
                vuln_fixes = vuln.get('fixes') or []
                if not vuln_fixes:
                    # Note: in order to add a vulnerability with no fixes we need to have an empty fix
                    vuln_fixes.append({})
                for fix in vuln_fixes:
                    try:
                        open_ports_vulns_and_fixes.append(DeviceOpenPortVulnerabilityAndFix(
                            port_id=vuln.get('port'),
                            cve_id=vuln.get('cve_id'),
                            cve_description=vuln.get('cve_description'),
                            cve_severity=vuln.get('severity'),
                            wasc_id=vuln.get('wasc_id'),
                            vuln_solution=vuln.get('solution'),
                            fix_title=fix.get('title'),
                            fix_diagnosis=fix.get('diagnosis'),
                            fix_consequence=fix.get('consequence'),
                            fix_solution=fix.get('solution'),
                            fix_url=fix.get('url'),
                            fix_updated_at=parse_date(fix.get('updated_at')),
                            patch_publication_date=parse_date(fix.get('patch_publication_date')),
                        ))
                    except Exception:
                        logger.exception(f'Failed to append vuln {vuln} and fix {fix}')
            device.open_ports_vulns_and_fixes = open_ports_vulns_and_fixes
            device.device_managed_by = device_raw.get('owner')
            if device.get('ec2'):
                device.cloud_provider = 'AWS'
                device.cloud_id = device_raw.get('ec2')
        except Exception:
            logger.exception(f'Failed filling generic fields of {device_raw}')

    @staticmethod
    def _fill_specific_fields(device: MyDeviceAdapter, device_raw):
        try:
            asset_id = device_raw.get('id')
            device.asset_id = asset_id
            if isinstance(device_raw.get('tags'), list):
                device.asset_tags = device_raw.get('tags')
            device.asset_groups = [AssetGroup(id=group.get('id'), name=group.get('name'))
                                   for group in (device_raw.get('asset_groups') or [])]
            device.fqdn = device_raw.get('fqdn')
            device.netbios_name = device_raw.get('netbios')
            device.external_id = device_raw.get('external_id')
            device.url = device_raw.get('url')
            device.affected_file = device_raw.get('file')
            device.database = device_raw.get('database')
            device.status = device_raw.get('status')
        except Exception:
            logger.exception(f'Failed filling specific fields of {device_raw}')

    def _create_device(self, device_raw):
        try:
            if not (isinstance(device_raw, tuple) and len(device_raw) == 2):
                logger.error(f'Invalid device_raw retrieved {device_raw}')
                return None
            device_raw, device_vulnerabilities = device_raw

            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('ip_address') or '')

            self._fill_generic_fields(device, device_raw, device_vulnerabilities)
            self._fill_specific_fields(device, device_raw)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Kenna Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        # AUTOADAPTER - check if you need to add other properties'
        return [AdapterProperty.Assets]
