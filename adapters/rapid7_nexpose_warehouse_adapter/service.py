import logging
from collections import defaultdict

from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from axonius.adapter_base import AdapterProperty
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.postgres.connection import PostgresConnection
from axonius.adapter_exceptions import ClientConnectionException
from rapid7_nexpose_warehouse_adapter import consts
from rapid7_nexpose_warehouse_adapter.client_id import get_client_id
from rapid7_nexpose_warehouse_adapter.structures import Rapid7NexposeWarehouseDeviceInstance, RapidAsset, RapidPolicy, \
    RapidInstalledSoftware, RapidService, RapidTag, RapidVulnerability, RapidUserAccount, RapidGroupAccount

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
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('server'),
                                                port=client_config.get('port'))

    @staticmethod
    def get_connection(client_config):
        connection = PostgresConnection(
            host=client_config['server'],
            port=int(client_config.get('port')),
            username=client_config['username'],
            password=client_config['password'],
            db_name=client_config.get('database'))

        connection.set_credentials(username=client_config['username'],
                                   password=client_config['password'])
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except Exception:
            message = f'Error connecting to client host: {client_config["server"]}  ' \
                      f'database: ' \
                      f'{client_config.get("database")}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    @staticmethod
    def _get_vulnerabilities_by_asset_id(connection):
        try:
            vulnerabilities_counter = 0
            vulnerabilities = {}
            asset_vulnerabilities = defaultdict(list)

            # Dict of vulnerabilities, keys are by vulnerability_id
            for vulnerability in connection.query(consts.VULNERABILITIES_QUERY):
                if isinstance(vulnerability, dict) and vulnerability.get('vulnerability_id'):
                    vulnerabilities[vulnerability.get('vulnerability_id')] = vulnerability

            for asset_vulnerability in connection.query(consts.ASSET_VULNERABILITIES_QUERY):
                if (isinstance(asset_vulnerability, dict) and
                        asset_vulnerability.get('vulnerability_id') and
                        asset_vulnerability.get('asset_id')):
                    if vulnerabilities.get(asset_vulnerability.get('vulnerability_id')):
                        vulnerabilities_counter += 1
                        asset_vulnerabilities[asset_vulnerability.get('asset_id')].append(
                            vulnerabilities.get(asset_vulnerability.get('vulnerability_id')))

            logger.debug(
                f'Fetching from vulnerabilities table completed successfully, total of {vulnerabilities_counter}')
            return asset_vulnerabilities
        except Exception:
            logger.warning(f'Failed getting vulnerabilities')
            return {}

    @staticmethod
    def _get_tags(connection):
        try:
            tags_counter = 0
            tags = {}
            asset_tags = defaultdict(list)

            # Dict of tags, keys are by tag_id
            for tag in connection.query(consts.TAGS_QUERY):
                if isinstance(tag, dict) and tag.get('tag_id'):
                    tags[tag.get('tag_id')] = tag

            for asset_tag in connection.query(consts.ASSET_TAGS_QUERY):
                if isinstance(asset_tag, dict) and asset_tag.get('tag_id') and asset_tag.get('asset_id'):
                    if tags.get(asset_tag.get('tag_id')):
                        tags_counter += 1
                        asset_tags[asset_tag.get('asset_id')].append(tags.get(asset_tag.get('tag_id')))

            logger.debug(f'Fetching from tags table completed successfully, total of {tags_counter}')
            return asset_tags
        except Exception:
            logger.warning(f'Failed getting tags')
            return {}

    @staticmethod
    def _get_users(connection):
        try:
            users_counter = 0
            users = defaultdict(list)
            for user in connection.query(consts.USERS_QUERY):
                if isinstance(user, dict) and user.get('asset_id'):
                    users_counter += 1
                    users[user.get('asset_id')].append(user)

            logger.debug(f'Fetching from users table completed successfully, total of {users_counter}')
            return users
        except Exception:
            logger.warning(f'Failed getting users')
            return {}

    @staticmethod
    def _get_groups(connection):
        try:
            groups_counter = 0
            groups = defaultdict(list)
            for group in connection.query(consts.GROUPS_QUERY):
                if isinstance(group, dict) and group.get('asset_id'):
                    groups_counter += 1
                    groups[group.get('asset_id')].append(group)

            logger.debug(f'Fetching from groups table completed successfully, total of {groups_counter}')
            return groups
        except Exception:
            logger.warning(f'Failed getting groups')
            return {}

    @staticmethod
    def _get_ports(connection):
        try:
            services_counter = 0
            services = defaultdict(list)
            for service in connection.query(consts.SERVICES_QUERY):
                if isinstance(service, dict) and service.get('asset_id'):
                    services_counter += 1
                    services[service.get('asset_id')].append(service)

            logger.debug(f'Fetching from services table completed successfully, total of {services_counter}')
            return services
        except Exception:
            logger.warning(f'Failed getting assets')
            return {}

    @staticmethod
    def _get_installed_software(connection):
        try:
            softwares_counter = 0
            softwares = defaultdict(list)
            for software in connection.query(consts.INSTALLED_SOFTWARE_QUERY):
                if isinstance(software, dict) and software.get('asset_id'):
                    softwares_counter += 1
                    softwares[software.get('asset_id')].append(software)

            logger.debug(f'Fetching from softwares table completed successfully, total of {softwares_counter}')
            return softwares
        except Exception as e:
            logger.warning(f'Failed getting softwares. {str(e)}')
            return {}

    @staticmethod
    def _get_policies(connection):
        try:
            policies_counter = 0
            policies = {}
            asset_policies = defaultdict(list)

            # Dict of vulnerabilities, keys are by vulnerability_id
            for policy in connection.query(consts.POLICIES_QUERY):
                if isinstance(policy, dict) and policy.get('policy_id'):
                    policies[policy.get('policy_id')] = policy

            for asset_policy in connection.query(consts.ASSET_POLICIES_QUERY):
                if (isinstance(asset_policy, dict) and
                        asset_policy.get('policy_id') and
                        asset_policy.get('asset_id')):
                    if policies.get(asset_policy.get('policy_id')):
                        policies_counter += 1
                        asset_policies[asset_policy.get('asset_id')].append(policies.get(asset_policy.get('policy_id')))

            logger.debug(f'Fetching from policies table completed successfully, total of {policies_counter}')
            return asset_policies
        except Exception:
            logger.warning(f'Failed getting policies')
            return {}

    @staticmethod
    def _get_devices(connection):
        try:
            asset_counter = 0
            devices = defaultdict(list)
            for device in connection.query(consts.ASSET_QUERY):
                if isinstance(device, dict) and device.get('asset_id'):
                    asset_counter += 1
                    devices[device.get('asset_id')].append(device)

            logger.debug(f'Fetching from assets table completed successfully, total of {asset_counter}')
            return devices
        except Exception:
            logger.warning(f'Failed getting assets')
            return {}

    def _get_devices_info(self, client_data):
        try:
            devices_info = {
                'vulnerabilities': self._get_vulnerabilities_by_asset_id(client_data),
                'users': self._get_users(client_data),
                'groups': self._get_groups(client_data),
                'tags': self._get_tags(client_data),
                'ports': self._get_ports(client_data),
                'installed_softwares': self._get_installed_software(client_data),
                'policies': self._get_policies(client_data)
            }

            logger.debug(f'Finished collecting and combining devices information')
            return devices_info
        except Exception:
            logger.warning('Failed getting device info')
            return {}

    @staticmethod
    def _build_device_info(devices_info: dict, device: dict, asset_id: str):
        try:
            if isinstance(devices_info.get('vulnerabilities'), dict) and devices_info.get('vulnerabilities'):
                device['extra_vulnerabilities'] = devices_info.get('vulnerabilities').get(asset_id) or []

            if isinstance(devices_info.get('users'), dict) and devices_info.get('users'):
                device['extra_users'] = devices_info.get('users').get(asset_id) or []

            if isinstance(devices_info.get('groups'), dict) and devices_info.get('groups'):
                device['extra_groups'] = devices_info.get('groups').get(asset_id) or []

            if isinstance(devices_info.get('tags'), dict) and devices_info.get('tags'):
                device['extra_tags'] = devices_info.get('tags').get(asset_id) or []

            if isinstance(devices_info.get('ports'), dict) and devices_info.get('ports'):
                device['extra_ports'] = devices_info.get('ports').get(asset_id) or []

            installed_softwares = devices_info.get('installed_softwares')
            if isinstance(installed_softwares, dict) and installed_softwares:
                device['extra_installed_softwares'] = devices_info.get('installed_softwares').get(asset_id) or []

            if isinstance(devices_info.get('policies'), dict) and devices_info.get('policies'):
                device['extra_policies'] = devices_info.get('policies').get(asset_id) or []

            return device
        except Exception:
            logger.exception('Failed building device info')

    def _query_devices_by_client(self, client_name, client_data: PostgresConnection):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        client_config = self._get_client_config_by_client_id(client_name)
        with client_data:
            client_data.set_devices_paging(consts.DEVICE_PAGINATION)
            devices_info = self._get_devices_info(client_data)
            logger.debug(f'Start querying dim_asset')
            for device in client_data.query(consts.ASSET_QUERY):
                if isinstance(device, dict) and client_config['drop_only_ip_devices']:
                    if not (device.get('mac_address') and device.get('host_name')):
                        continue
                if isinstance(device, dict) and device.get('asset_id'):
                    self._build_device_info(devices_info, device, device.get('asset_id'))
                yield device

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
                'database'
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

            if isinstance(device_raw, list):
                for vulnerability in device_raw:
                    if isinstance(vulnerability, dict):
                        rapid_vulnerability = RapidVulnerability()

                        rapid_vulnerability.vulnerability_id = vulnerability.get('vulnerability_id')
                        rapid_vulnerability.nexpose_id = vulnerability.get('nexpose_id')
                        rapid_vulnerability.title = vulnerability.get('title')
                        rapid_vulnerability.description = vulnerability.get('description')
                        rapid_vulnerability.date_published = parse_date(vulnerability.get('date_published'))
                        rapid_vulnerability.date_added = parse_date(vulnerability.get('date_added'))
                        rapid_vulnerability.date_modified = parse_date(vulnerability.get('date_modified'))
                        rapid_vulnerability.severity_score = vulnerability.get('severity_score')
                        rapid_vulnerability.severity = vulnerability.get('severity')
                        rapid_vulnerability.critical = vulnerability.get('critical')
                        rapid_vulnerability.severe = vulnerability.get('severe')
                        rapid_vulnerability.moderate = vulnerability.get('moderate')
                        rapid_vulnerability.pci_severity_score = vulnerability.get('pci_severity_score')
                        rapid_vulnerability.pci_status = vulnerability.get('pci_status')
                        rapid_vulnerability.pci_failures = vulnerability.get('pci_failures')
                        rapid_vulnerability.risk_score = _parse_float(vulnerability.get('risk_score'))
                        rapid_vulnerability.cvss_vector = vulnerability.get('cvss_vector')
                        rapid_vulnerability.cvss_access_vector = vulnerability.get('cvss_access_vector')
                        rapid_vulnerability.cvss_access_complexity = vulnerability.get('cvss_access_complexity')
                        rapid_vulnerability.cvss_authentication = vulnerability.get('cvss_authentication')
                        rapid_vulnerability.cvss_confidentiality_impact = vulnerability.get(
                            'cvss_confidentiality_impact')
                        rapid_vulnerability.cvss_integrity_impact = vulnerability.get('cvss_integrity_impact')
                        rapid_vulnerability.cvss_availability_impact = vulnerability.get('cvss_availability_impact')
                        rapid_vulnerability.cvss_score = _parse_float(vulnerability.get('cvss_score'))
                        rapid_vulnerability.pci_adjusted_cvss_score = _parse_float(
                            vulnerability.get('pci_adjusted_cvss_score'))
                        rapid_vulnerability.cvss_exploit_score = _parse_float(
                            vulnerability.get('cvss_exploit_score'))
                        rapid_vulnerability.cvss_impact_score = _parse_float(
                            vulnerability.get('cvss_impact_score'))
                        rapid_vulnerability.pci_special_notes = vulnerability.get('pci_special_notes')
                        rapid_vulnerability.denial_of_service = vulnerability.get('denial_of_service')
                        rapid_vulnerability.exploits = vulnerability.get('exploits')
                        rapid_vulnerability.exploit_skill_level = vulnerability.get('exploit_skill_level')
                        rapid_vulnerability.malware_kits = vulnerability.get('malware_kits')
                        rapid_vulnerability.malware_popularity = vulnerability.get('malware_popularity')
                        rapid_vulnerability.cvss_v3_vector = vulnerability.get('cvss_v3_vector')
                        rapid_vulnerability.cvss_v3_attack_vector = vulnerability.get('cvss_v3_attack_vector')
                        rapid_vulnerability.cvss_v3_attack_complexity = vulnerability.get('cvss_v3_attack_complexity')
                        rapid_vulnerability.cvss_v3_privileges_required = vulnerability.get(
                            'cvss_v3_privileges_required')
                        rapid_vulnerability.cvss_v3_user_interaction = vulnerability.get('cvss_v3_user_interaction')
                        rapid_vulnerability.cvss_v3_scope = vulnerability.get('cvss_v3_scope')
                        rapid_vulnerability.cvss_v3_confidentiality_impact = vulnerability.get(
                            'cvss_v3_confidentiality_impact')
                        rapid_vulnerability.cvss_v3_integrity_impact = vulnerability.get('cvss_v3_integrity_impact')
                        rapid_vulnerability.cvss_v3_availability_impact = vulnerability.get(
                            'cvss_v3_availability_impact')
                        rapid_vulnerability.cvss_v3_score = _parse_float(vulnerability.get('cvss_v3_score'))
                        rapid_vulnerability.cvss_v3_impact_score = _parse_float(
                            vulnerability.get('cvss_v3_impact_score'))
                        rapid_vulnerability.cvss_v3_exploit_score = _parse_float(
                            vulnerability.get('cvss_v3_exploit_score'))

                        rapid_vulnerabilities.append(rapid_vulnerability)

                        # Duplicate data for Aggregated Data
                        device.add_vulnerable_software(cvss=vulnerability.get('cvss_score'),
                                                       cve_id=vulnerability.get('vulnerability_id'),
                                                       cve_description=vulnerability.get('description'))

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

                        rapid_tag.id = tag.get('id')
                        rapid_tag.name = tag.get('name')
                        rapid_tag.type_ = tag.get('type_')
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
            rapid_installed_softwares = []

            if isinstance(device_raw, list):
                for installed_software in device_raw:
                    if isinstance(installed_software, dict):
                        rapid_installed_software = RapidInstalledSoftware()

                        rapid_installed_software.id = installed_software.get('id')
                        rapid_installed_software.vendor = installed_software.get('vendor')
                        rapid_installed_software.family = installed_software.get('family')
                        rapid_installed_software.name = installed_software.get('name')
                        rapid_installed_software.version = installed_software.get('version')
                        rapid_installed_software.type_ = installed_software.get('type')
                        rapid_installed_software.cpe = installed_software.get('cpe')

                        rapid_installed_softwares.append(rapid_installed_software)

                        # Duplicate data for Aggregated Data
                        device.add_installed_software(vendor=installed_software.get('vendor'),
                                                      name=installed_software.get('name'),
                                                      version=installed_software.get('version'))

                device.rapid_installed_softwares = rapid_installed_softwares
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

                        rapid_policy.id = policy.get('id')
                        rapid_policy.benchmark_id = policy.get('benchmark_id')
                        rapid_policy.name = policy.get('name')
                        rapid_policy.version = policy.get('version')
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
            device.id = device_id

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

            device.set_raw(device_raw)
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
