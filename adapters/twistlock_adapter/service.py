import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
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


class TwistlockVuln(SmartJsonClass):
    applicable_rules = ListField(str, 'Applicable Rules')
    cause = Field(str, 'Cause')
    cve = Field(str, 'CVE')
    cvss = Field(float, 'CVSS')
    description = Field(str, 'Description')
    discovered = Field(datetime.datetime, 'Discovered')
    exploit = Field(str, 'Exploit')
    link = Field(str, 'Link')
    layer_time = Field(datetime.datetime, 'Layer Time')
    package_time = Field(str, 'Package Time')
    package_verson = Field(str, 'Package Version')
    published = Field(datetime.datetime, 'Published')
    severity = Field(str, 'Severity')
    status = Field(str, 'Status')
    text = Field(str, 'Text')
    type = Field(str, 'Type')
    vec_str = Field(str, 'Vec Str')
    title = Field(str, 'Title')
    templates = Field(str, 'Templates')
    twistlock = Field(bool, 'Twistlock')


class TwistlockContainer(SmartJsonClass):
    id = Field(str, 'Container ID')
    mac = Field(str, 'MAC Address')
    ips = ListField(str, 'IP Addresses')
    scantime = Field(datetime.datetime, 'Host Scan Time')
    name = Field(str, 'Conatiner Name')
    container_app = Field(str, 'Container Application')
    image_name = Field(str, 'Image Name')
    profile_id = Field(str, 'Profile ID')
    compliance_risk_score = Field(str, 'Compliance Risk Score')
    compliance_distribution = Field(VulnerabilitiesCount, 'Compliance Distribution')


class TwistlockAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        containers_data = ListField(TwistlockContainer, 'Containers Data')
        compliance_risk_score = Field(str, 'Compliance Risk Score')
        compliance_distribution = Field(VulnerabilitiesCount, 'Compliance Distribution')
        scantime = Field(datetime.datetime, 'Host Scan Time')
        last_modified = Field(datetime.datetime, 'Last Modified')
        agent_type = Field(str, 'Agent Type')
        is_connected = Field(bool, 'Is Connected')
        proxy_listener_type = Field(str, 'Proxy Listener Type')
        proxy_target_type = Field(str, 'Proxy Target Type')
        registry_scanner = Field(bool, 'Registry Scanner')
        cve_vulnerability_distribution = Field(VulnerabilitiesCount, 'CVE Vulnerability Distribution')
        profile_id = Field(str, 'Profile ID')
        twistlock_vulns = ListField(TwistlockVuln, 'Twistlock Vulnerabilities')

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
    def _connect_client(client_config):
        try:
            with TwistlockConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                     username=client_config['username'], password=client_config['password'],
                                     https_proxy=client_config.get('https_proxy'),
                                     tenant_name=client_config.get('tenant_name')
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
                    'name': 'tenant_name',
                    'title': 'Tenant Name',
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

    @staticmethod
    def _create_container_device(device_raw):
        try:
            device = TwistlockContainer()
            device.id = device_raw.get('_id')
            device.scantime = parse_date(device_raw.get('scanTime'))
            device_info = device_raw.get('info') or {}
            device.mac = device_info.get('MacAddress') if device_info.get('MacAddress') else None
            device.ips = device_info.get('IPAddress').split(',') if device_info.get('IPAddress') else None
            device.name = device_info.get('name')
            device.container_app = device_info.get('app')
            device.image_name = device_info.get('imageName')
            device.profile_id = device_info.get('profileID')
            compliance_distribution_raw = device_info.get('complianceDistribution')
            device.compliance_risk_score = device_raw.get('complianceRiskScore')
            if compliance_distribution_raw and isinstance(compliance_distribution_raw, dict):
                compliance_distribution = VulnerabilitiesCount()
                for key, value in compliance_distribution_raw.items():
                    try:
                        # pylint: disable=E1137
                        compliance_distribution[key] = value
                    except Exception:
                        logger.exception(f'Problem with key {key} and value {value}')
                device.compliance_distribution = compliance_distribution
            return device
        except Exception:
            logger.exception(f'Problem with container device {device_raw}')
            return None

    @staticmethod
    def _create_defender_device(device, device_raw):
        try:
            ips = device_raw.get('ips')
            try:
                if ips and isinstance(ips, list):
                    ips = [ip.strip() for ip in ips if ip and ip.strip()]
                    device.add_nic(None, ips)
            except Exception:
                logger.exception(f'Problem adding nic to {device_raw}')
            device.add_agent_version(agent=AGENT_NAMES.twistlock, version=device_raw.get('version'))
            device.agent_type = device_raw.get('type')
            device.last_modified = parse_date(device_raw.get('lastModified'))
            device.last_seen = parse_date(device_raw.get('lastModified'))
            try:
                ips = device_raw.get('hostIPs')
                if ips and isinstance(ips, list):
                    device.add_nic(None, ips)
            except Exception:
                logger.exception(f'Problem adding nic to {device_raw}')
            device.is_connected = device_raw.get('connected')
            agent_features = device_raw.get('features')
            if isinstance(agent_features, dict) and agent_features:
                device.registry_scanner = agent_features.get('registryScanner')
                device.proxy_target_type = agent_features.get('proxyTargetType')
                device.proxy_listener_type = agent_features.get('proxyListenerType')
        except Exception:
            logger.exception(f'Problem with defender device {device_raw}')

    # pylint: disable=R0912,R1702
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    @staticmethod
    def _create_host_device(device, device_raw):
        try:
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
                packages = device_data.get('packages') or device_raw.get('packages')
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
            device.compliance_risk_score = device_raw.get('complianceRiskScore')
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
            vulnerabilities_raw = device_raw.get('vulnerabilities')
            if not isinstance(vulnerabilities_raw, list):
                vulnerabilities_raw = []
            for vulnerability_raw in vulnerabilities_raw:
                try:
                    if not isinstance(vulnerability_raw, dict):
                        continue
                    device.add_vulnerable_software(cve_id=vulnerability_raw.get('cve'))
                    applicable_rules = vulnerability_raw.get('applicableRules')
                    if not isinstance(applicable_rules, list):
                        applicable_rules = None
                    cvss = None
                    try:
                        cvss = float(vulnerability_raw.get('cvss'))
                    except Exception:
                        pass
                    twistlock = vulnerability_raw.get('twistlock')
                    if not isinstance(twistlock, bool):
                        twistlock = None
                    layer_time = parse_date(vulnerability_raw.get('layerTime'))
                    twist_vuln_obj = TwistlockVuln(applicable_rules=applicable_rules,
                                                   cause=vulnerability_raw.get('cause'),
                                                   cve=vulnerability_raw.get('cve'),
                                                   description=vulnerability_raw.get('description'),
                                                   discovered=parse_date(vulnerability_raw.get('discovered')),
                                                   cvss=cvss,
                                                   exploit=vulnerability_raw.get('exploit'),
                                                   link=vulnerability_raw.get('link'),
                                                   layer_time=layer_time,
                                                   package_time=vulnerability_raw.get('packageName'),
                                                   package_verson=vulnerability_raw.get('packageVersion'),
                                                   published=parse_date(vulnerability_raw.get('published')),
                                                   severity=vulnerability_raw.get('severity'),
                                                   status=vulnerability_raw.get('status'),
                                                   twistlock=twistlock,
                                                   text=vulnerability_raw.get('text'),
                                                   type=vulnerability_raw.get('type'),
                                                   title=vulnerability_raw.get('title'),
                                                   templates=vulnerability_raw.get('templates'),
                                                   vec_str=vulnerability_raw.get('vecStr'))
                    device.twistlock_vulns.append(twist_vuln_obj)
                except Exception:
                    logger.exception(f'Problem with vulnerability raw {vulnerability_raw}')
        except Exception:
            logger.exception(f'Problem with host device {device_raw}')

    def _parse_raw_data(self, devices_raw_data):
        device_dict = dict()
        for device_raw, device_type in devices_raw_data:
            hostname = device_raw.get('hostname')
            if not hostname:
                logger.error(f'Twistlock device with no hostname {device_raw}')
                continue
            hostname = str(hostname).lower()
            if hostname not in device_dict:
                device_dict[hostname] = [self._new_device_adapter(), {'containers_data': []}]
                device_dict[hostname][0].id = hostname
                device_dict[hostname][0].hostname = hostname
            if device_type == CONTAINERS_NAME:
                container_data = self._create_container_device(device_raw)
                if container_data:
                    device_dict[hostname][0].containers_data.append(container_data)
                device_dict[hostname][1]['containers_data'].append(device_raw)
            elif device_type == HOSTS_NAME:
                self._create_host_device(device_dict[hostname][0], device_raw)
                device_dict[hostname][1]['host_data'] = device_raw
            elif device_type == DEFENDERS_NAME:
                self._create_defender_device(device_dict[hostname][0], device_raw)
                device_dict[hostname][1]['agent_data'] = device_raw
        for device, raw_data in device_dict.values():
            device.set_raw(raw_data)
            yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
