import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.smart_json_class import SmartJsonClass
from twistlock_adapter.connection import TwistlockConnection
from twistlock_adapter.client_id import get_client_id
from twistlock_adapter.consts import CONTAINERS_NAME, HOSTS_NAME, DEFENDERS_NAME


logger = logging.getLogger(f'axonius.{__name__}')


class VulnerabilitiesCount(SmartJsonClass):
    critical = Field(int, 'Critical')
    high = Field(int, 'High')
    medium = Field(int, 'Medium')
    low = Field(int, 'Low')
    total = Field(int, 'Total')


class TwistlockAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        agent_type = Field(str, 'Agent Type')
        is_connected = Field(bool, 'Is Connected')
        proxy_listener_type = Field(str, 'Proxy Listener Type')
        proxy_target_type = Field(str, 'Proxy Target Type')
        registry_scanner = Field(bool, 'Registry Scanner')
        scantime = Field(datetime.datetime, 'Host Scan Time')
        cve_vulnerability_distribution = Field(VulnerabilitiesCount, 'CVE Vulnerability Distribution')
        compliance_distribution = Field(VulnerabilitiesCount, 'Compliance Distribution')
        container_app = Field(str, 'Container Application')
        image_name = Field(str, 'Image Name')
        profile_id = Field(str, 'Profile ID')
        last_modified = Field(datetime.datetime, 'Last Modified')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with TwistlockConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                     username=client_config['username'], password=client_config['password'],
                                     ) as connection:
                return connection
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
        The schema TwistlockAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Twistlock Domain',
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

    def _create_container_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            if not device_raw.get('_id'):
                logger.warning(f'Bad device with no id {device_raw}')
                return None
            device.id = 'CONTAINER_' + device_raw.get('_id') + '_' + (device_raw.get('hostname') or '')
            device.hostname = device_raw.get('hostname')
            device.scantime = parse_date(device_raw.get('scanTime'))
            device_info = device_raw.get('info') or {}
            mac = device_info.get('MacAddress') if device_info.get('MacAddress') else None
            ips = device_info.get('IPAddress').split(',') if device_info.get('IPAddress') else None
            if mac or ips:
                device.add_nic(mac, ips)
            device.name = device_info.get('name')
            device.container_app = device_info.get('app')
            device.image_name = device_info.get('imageName')
            device.profile_id = device_info.get('profileID')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with container device {device_raw}')
            return None

    def _create_defender_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            if not device_raw.get('hostname'):
                logger.warning(f'Bad device with no Host name {device_raw}')
                return None
            device.id = 'AGENT_' + device_raw.get('hostname') + '_' + (device_raw.get('ips') or '')
            device.hostname = device_raw.get('hostname')
            ips = device_raw.get('ips')
            try:
                if ips and isinstance(ips, list):
                    ips = [ip.strip() for ip in ips if ip and ip.strip()]
                    device.add_nic(None, ips)
            except Exception:
                logger.exception(f'Problem adding nic to {device_raw}')
            device.agent_version = device_raw.get('version')
            device.agent_type = device_raw.get('type')
            device.last_modified = parse_date(device_raw.get('lastModified'))
            device.is_connected = device_raw.get('connected')
            agent_features = device_raw.get('features')
            if isinstance(agent_features, dict) and agent_features:
                device.registry_scanner = agent_features.get('registryScanner')
                device.proxy_target_type = agent_features.get('proxyTargetType')
                device.proxy_listener_type = agent_features.get('proxyListenerType')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with defender device {device_raw}')
            return None

    # pylint: disable=R0912,R1702
    def _create_host_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            if not device_raw.get('hostname'):
                logger.warning(f'Bad device with no Host name {device_raw}')
                return None
            device.id = 'HOST_' + device_raw.get('hostname')
            device.hostname = device_raw.get('hostname')
            device.scantime = parse_date(device_raw.get('scanTime'))
            device_info = device_raw.get('info') or {}
            try:
                device.figure_os(device_info.get('distro'))
            except Exception:
                logger.exception(f'Problem getting OS for {device_raw}')
            try:
                device_data = device_info.get('data')
                if not device_data or not isinstance(device_data, dict):
                    device_data = {}
                packages = device_data.get('packages')
                if packages and isinstance(packages, list):
                    for package in packages:
                        try:
                            if isinstance(package, dict) and isinstance(package.get('pkgs'), list):
                                for pkg_item in package.get('pkgs'):
                                    try:
                                        device.add_installed_software(name=pkg_item.get('name'),
                                                                      version=pkg_item.get('version'),
                                                                      cve_count=pkg_item.get('cveCount'),
                                                                      sw_license=pkg_item.get('license'))
                                    except Exception:
                                        logger.exception(f'Problem with package item')
                        except Exception:
                            logger.exception(f'Problem adding package {package}')
            except Exception:
                logger.exception(f'Problem adding sw to {device_raw}')
            compliance_distribution_raw = device_info.get('complianceDistribution')
            if compliance_distribution_raw and isinstance(compliance_distribution_raw, dict):
                compliance_distribution = VulnerabilitiesCount()
                for key, value in compliance_distribution_raw.items():
                    try:
                        # pylint: disable=E1137
                        compliance_distribution[key] = value
                    except Exception:
                        logger.exception(f'Problem with key {key} and value {value}')
                device.compliance_distribution = compliance_distribution

            cve_vulnerability_distribution_raw = device_info.get('cveVulnerabilityDistribution')
            if cve_vulnerability_distribution_raw and isinstance(cve_vulnerability_distribution_raw, dict):
                cve_vulnerability_distribution = VulnerabilitiesCount()
                for key, value in cve_vulnerability_distribution_raw.items():
                    try:
                        # pylint: disable=E1137
                        cve_vulnerability_distribution[key] = value
                    except Exception:
                        logger.exception(f'Problem with key {key} and value {value}')
                device.cve_vulnerability_distribution = cve_vulnerability_distribution

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with host device {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            device = None
            if device_type == CONTAINERS_NAME:
                device = self._create_container_device(device_raw)
            elif device_type == HOSTS_NAME:
                device = self._create_host_device(device_raw)
            elif device_type == DEFENDERS_NAME:
                device = self._create_defender_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        # AUTOADAPTER - check if you need to add other properties'
        return [AdapterProperty.Assets]
