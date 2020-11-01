import logging

from axonius.devices.device_adapter import get_settings_cached
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from axonius.adapter_base import AdapterProperty
from axonius.clients.rest.connection import RESTConnection
from axonius.fields import Field
from axonius.multiprocess.multiprocess import concurrent_multiprocess_yield
from axonius.adapter_exceptions import ClientConnectionException
from rapid7_nexpose_warehouse_adapter.client_id import get_client_id
from rapid7_nexpose_warehouse_adapter.parse import _query_devices_by_client_rapid7_warehouse, \
    get_rapid7_warehouse_connection
from rapid7_nexpose_warehouse_adapter.structures import Rapid7NexposeWarehouseDeviceInstance, RapidAsset, RapidPolicy, \
    RapidService, RapidTag, RapidVulnerability, RapidUserAccount, RapidGroupAccount

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


def _parse_float(value=None):
    try:
        return float(value)
    except Exception as e:
        if value is not None:
            logger.warning(f'Failed to parse {value} as float: {str(e)}')
    return None


class Rapid7NexposeWarehouseAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(Rapid7NexposeWarehouseDeviceInstance):
        device_type = Field(str, 'Device Type')

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('server'),
                                                port=client_config.get('port'))

    def _connect_client(self, client_config):
        try:
            get_rapid7_warehouse_connection(client_config)
            return client_config
        except Exception:
            message = f'Error connecting to client host: {client_config["server"]}  ' \
                      f'database: ' \
                      f'{client_config.get("database")}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string(force_show_traceback=True))

    def _query_devices_by_client(self, client_name, client_data: dict):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        _ = (yield from concurrent_multiprocess_yield(
            [
                (
                    _query_devices_by_client_rapid7_warehouse,
                    (
                        client_data,
                    ),
                    {}
                )
            ],
            1
        ))

    def _clients_schema(self):
        """
        The schema Rapid7NexposeWarehouseAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'server',
                    'title': 'PostgreSQL Server',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'default': 5432,
                    'format': 'port'
                },
                {
                    'name': 'database',
                    'title': 'Database',
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
                    'name': 'drop_only_ip_devices',
                    'title': 'Do not fetch devices with no MAC address and no hostname',
                    'type': 'bool',
                    'default': False
                }
            ],
            'required': [
                'server',
                'username',
                'password',
                'database',
                'port',
                'drop_only_ip_devices'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_rapid7_nexpose_warehouse_groups_fields(device_raw: list, device: MyDeviceAdapter):
        try:
            rapid_groups = []

            if isinstance(device_raw, list):
                for group in device_raw:
                    if isinstance(group, dict):
                        rapid_group = RapidGroupAccount()

                        rapid_group.name = group.get('name')

                        rapid_groups.append(rapid_group)

            device.rapid_groups = rapid_groups
        except Exception:
            logger.warning(f'Failed to fill groups fields')

    @staticmethod
    def _fill_rapid7_nexpose_warehouse_users_fields(device_raw: list, device: MyDeviceAdapter):
        try:
            rapid_users = []

            if isinstance(device_raw, list):
                for user in device_raw:
                    if isinstance(user, dict):
                        rapid_user = RapidUserAccount()

                        rapid_user.name = user.get('name')
                        rapid_user.full_name = user.get('full_name')

                        rapid_users.append(rapid_user)

                        # Duplicate data for Aggregated Data
                        device.add_users(username=user.get('name'))

            device.rapid_users = rapid_users
        except Exception:
            logger.warning(f'Failed to fill users fields')

    @staticmethod
    # pylint: disable=too-many-statements, invalid-name
    def _fill_rapid7_nexpose_warehouse_vulnerabilities_fields(device_raw: list, device: MyDeviceAdapter):
        try:
            rapid_vulnerabilities = []
            device.software_cves = []

            if isinstance(device_raw, list):
                for vulnerability in device_raw:
                    if isinstance(vulnerability, dict):
                        rapid_vulnerability = RapidVulnerability()

                        rapid_vulnerability.vulnerability_id = vulnerability.get('vulnerability_id')
                        rapid_vulnerability.nexpose_id = vulnerability.get('nexpose_id')
                        rapid_vulnerability.title = vulnerability.get('title')
                        rapid_vulnerability.severity = vulnerability.get('severity')

                        if get_settings_cached()['should_populate_heavy_fields']:
                            rapid_vulnerability.date_published = parse_date(vulnerability.get('date_published'))
                            rapid_vulnerability.date_added = parse_date(vulnerability.get('date_added'))
                            rapid_vulnerability.date_modified = parse_date(vulnerability.get('date_modified'))
                            rapid_vulnerability.severity_score = vulnerability.get('severity_score')
                            rapid_vulnerability.critical = vulnerability.get('critical')
                            rapid_vulnerability.severe = vulnerability.get('severe')
                            rapid_vulnerability.moderate = vulnerability.get('moderate')
                            rapid_vulnerability.pci_severity_score = vulnerability.get('pci_severity_score')
                            rapid_vulnerability.pci_status = vulnerability.get('pci_status')
                            rapid_vulnerability.pci_failures = vulnerability.get('pci_failures')
                            rapid_vulnerability.risk_score = _parse_float(vulnerability.get('risk_score'))
                            rapid_vulnerability.cvss_vector = vulnerability.get('cvss_vector')
                            rapid_vulnerability.cvss_score = _parse_float(vulnerability.get('cvss_score'))
                            rapid_vulnerability.pci_adjusted_cvss_score = _parse_float(
                                vulnerability.get('pci_adjusted_cvss_score'))
                            rapid_vulnerability.denial_of_service = vulnerability.get('denial_of_service')
                            rapid_vulnerability.exploits = vulnerability.get('exploits')
                            rapid_vulnerability.malware_kits = vulnerability.get('malware_kits')
                            rapid_vulnerability.malware_popularity = vulnerability.get('malware_popularity')
                            rapid_vulnerability.cvss_v3_vector = vulnerability.get('cvss_v3_vector')
                            rapid_vulnerability.cvss_v3_score = _parse_float(vulnerability.get('cvss_v3_score'))

                        rapid_vulnerabilities.append(rapid_vulnerability)
            device.rapid_vulnerabilities = rapid_vulnerabilities
        except Exception:
            logger.warning(f'Failed to fill vulnerabilities fields')

    @staticmethod
    def _fill_rapid7_nexpose_warehouse_tags_fields(device_raw: list, device: MyDeviceAdapter):
        try:
            rapid_tags = []

            if isinstance(device_raw, list):
                for tag in device_raw:
                    if isinstance(tag, dict):
                        rapid_tag = RapidTag()

                        rapid_tag.id = tag.get('tag_id')
                        rapid_tag.name = tag.get('name')
                        rapid_tag.type_ = tag.get('type')
                        rapid_tag.source = tag.get('source')
                        rapid_tag.created = parse_date(tag.get('created'))
                        rapid_tag.risk_modifier = _parse_float(tag.get('risk_modifier'))
                        rapid_tag.color = tag.get('color')

                        rapid_tags.append(rapid_tag)

                        # Duplicate data for Aggregated Data
                        key = tag.get('id') or tag.get('name') or ''
                        val = tag.get('source')
                        device.add_key_value_tag(key=key, value=val)

            device.rapid_tags = rapid_tags
        except Exception:
            logger.warning(f'Failed to fill tags fields')

    @staticmethod
    def _fill_rapid7_nexpose_warehouse_ports_fields(device_raw: list, device: MyDeviceAdapter):
        try:
            rapid_services = []

            if isinstance(device_raw, list):
                for service in device_raw:
                    if isinstance(service, dict):
                        rapid_service = RapidService()

                        rapid_service.id = service.get('id')
                        rapid_service.service = service.get('service')
                        rapid_service.port = service.get('port')
                        rapid_service.protocol = service.get('protocol')
                        rapid_service.vendor = service.get('vendor')
                        rapid_service.family = service.get('family')
                        rapid_service.name = service.get('name')
                        rapid_service.version = service.get('version')
                        rapid_service.certainty = _parse_float(service.get('certainty'))
                        rapid_service.credential_status = service.get('credential_status')

                        rapid_services.append(rapid_service)

                        # Duplicate data for Aggregated Data
                        device.add_open_port(protocol=service.get('protocol'),
                                             port_id=service.get('port'),
                                             service_name=service.get('name'))

            device.rapid_services = rapid_services
        except Exception:
            logger.warning(f'Failed to fill services fields')

    @staticmethod
    # pylint: disable=invalid-name
    def _fill_rapid7_nexpose_warehouse_installed_softwares_fields(device_raw: list, device: MyDeviceAdapter):
        try:
            if isinstance(device_raw, list):
                for installed_software in device_raw:
                    if isinstance(installed_software, dict):
                        device.add_installed_software(vendor=installed_software.get('vendor'),
                                                      name=installed_software.get('name'),
                                                      version=installed_software.get('version'))
        except Exception as e:
            logger.warning(f'Failed to fill installed softwares fields {str(e)}')

    @staticmethod
    def _fill_rapid7_nexpose_warehouse_policies_fields(device_raw: list, device: MyDeviceAdapter):
        try:
            rapid_policies = []
            if isinstance(device_raw, list):
                for policy in device_raw:
                    if isinstance(policy, dict):
                        rapid_policy = RapidPolicy()

                        rapid_policy.id = policy.get('policy_id')
                        rapid_policy.benchmark_id = policy.get('benchmark_id')
                        rapid_policy.name = policy.get('policy_name')
                        rapid_policy.version = policy.get('policy_version')
                        rapid_policy.title = policy.get('title')
                        rapid_policy.description = policy.get('description')
                        rapid_policy.unscored_rules = policy.get('unscored_rules')

                        rapid_policies.append(rapid_policy)
                device.rapid_policies = rapid_policies
        except Exception:
            logger.warning(f'Failed to fill policies fields')

    @staticmethod
    def _fill_rapid7_nexpose_warehouse_asset_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            rapid_asset = RapidAsset()

            rapid_asset.credential_status = device_raw.get('credential_status')
            rapid_asset.risk_modifier = _parse_float(device_raw.get('risk_modifier'))
            rapid_asset.last_assessed_vulnerabilities = parse_date(device_raw.get(
                'last_assessed_for_vulnerabilities'))

            try:
                sites = device_raw.get('sites') or []
                if isinstance(sites, str) and not sites.startswith('['):
                    sites = sites.split(',')
                rapid_asset.sites = sites
            except Exception:
                logger.debug(f'Failed getting asset sites property for {sites}')

            device.rapid_asset = rapid_asset
        except Exception:
            logger.warning(f'Failed to fill asset fields')

    def _fill_rapid7_nexpose_warehouse_device_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            self._fill_rapid7_nexpose_warehouse_asset_fields(device_raw, device)

            if device_raw.get('extra_vulnerabilities'):
                self._fill_rapid7_nexpose_warehouse_vulnerabilities_fields(device_raw.get('extra_vulnerabilities'),
                                                                           device)

            if device_raw.get('extra_users'):
                self._fill_rapid7_nexpose_warehouse_users_fields(device_raw.get('extra_users'),
                                                                 device)

            if device_raw.get('extra_groups'):
                self._fill_rapid7_nexpose_warehouse_groups_fields(device_raw.get('extra_groups'),
                                                                  device)

            if device_raw.get('extra_tags'):
                self._fill_rapid7_nexpose_warehouse_tags_fields(device_raw.get('extra_tags'), device)

            if device_raw.get('extra_ports'):
                self._fill_rapid7_nexpose_warehouse_ports_fields(device_raw.get('extra_ports'), device)

            if device_raw.get('extra_installed_softwares'):
                self._fill_rapid7_nexpose_warehouse_installed_softwares_fields(
                    device_raw.get('extra_installed_softwares'), device)

            if device_raw.get('extra_policies'):
                self._fill_rapid7_nexpose_warehouse_policies_fields(device_raw.get('extra_policies'), device)

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('asset_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('host_name') or '')

            device.hostname = device_raw.get('host_name')
            device.device_type = device_raw.get('host_type')

            ips = device_raw.get('ip_address') or []
            if isinstance(ips, str):
                ips = [ips]
            device.add_nic(mac=device_raw.get('mac_address'), ips=ips)

            os_string = f'{device_raw.get("os_vendor") or ""} {device_raw.get("os_family") or ""} '
            os_string += f'{device_raw.get("os_version") or ""} {device_raw.get("os_architecture") or ""} '
            os_string += f'{device_raw.get("os_type") or ""} {device_raw.get("os_name") or ""} '
            os_string += f'{device_raw.get("os_description") or ""} {device_raw.get("os_system") or ""} '
            os_string += f'{device_raw.get("os_cpe") or ""}'
            device.figure_os(os_string=os_string)

            self._fill_rapid7_nexpose_warehouse_device_fields(device_raw, device)
            dict_raw = dict()
            for key in device_raw:
                dict_raw[str(key)] = str(device_raw[key])
            device.set_raw(dict_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Rapid7 Nexpose Warehouse Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Rapid7NexposeWarehouse Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Vulnerability_Assessment]
