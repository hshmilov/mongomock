import datetime
import logging

from typing import List

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_domain_valid
from crowd_strike_adapter import consts
from crowd_strike_adapter.connection import CrowdStrikeConnection

logger = logging.getLogger(f'axonius.{__name__}')


class Group(SmartJsonClass):
    created_by = Field(str, 'Created By')
    created_timestamp = Field(datetime.datetime, 'Created Time')
    description = Field(str, 'Description')
    group_type = Field(str, 'Group Type')
    id = Field(str, 'Id')
    modified_by = Field(str, 'Modified By')
    modified_time = Field(datetime.datetime, 'Modified Time')
    name = Field(str, 'Name')


class PolicySettingValue(SmartJsonClass):
    enabled = Field(bool, 'Enabled')


class PolicySettings(SmartJsonClass):
    id = Field(str, 'Id')
    name = Field(str, 'name')
    description = Field(str, 'Description')
    value = Field(PolicySettingValue, 'Value')


class PreventionSettings(SmartJsonClass):
    name = Field(str, 'Name')
    settings = ListField(PolicySettings, 'Settings')


class SensorUpdateSettings(SmartJsonClass):
    build = Field(str, 'Build')


class Policy(SmartJsonClass):
    name = Field(str, 'Name')
    description = Field(str, 'Description')
    platform_name = Field(str, 'Platform Name')
    groups = ListField(Group, 'Groups')
    enabled = Field(bool, 'Enabled')
    created_by = Field(str, 'Created By')
    created_time = Field(datetime.datetime, 'Created Time')
    prevention_settings = ListField(PreventionSettings, 'Prevention Settings')
    sensor_update_settings = Field(SensorUpdateSettings, 'Sensor Update Settings')


class SpotlightVulnerability(SmartJsonClass):
    created_timestamp = Field(datetime.datetime, 'Created Time')
    closed_timestamp = Field(datetime.datetime, 'Closed Time')
    status = Field(str, 'Status')
    cve_id = Field(str, 'CVE')
    cve_score = Field(int, 'CVE Score')
    cve_severity = Field(str, 'CVE Severity')
    application_name = Field(str, 'Application Name')


class CrowdStrikeAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        external_ip = Field(str, 'External IP')
        groups = ListField(Group, 'Groups')
        prevention_policy = Field(Policy, 'Prevention Policy')
        sensor_update_policy = Field(Policy, 'Sensor Update Policy')
        cs_agent_version = Field(str, 'CrowdStrike Agent Version')
        system_product_name = Field(str, 'System Product Name')
        full_osx_version = Field(str, 'Full OS X Version')
        spotlight_vulnerabilities = ListField(SpotlightVulnerability, 'Device Vulnerabilities')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def action(self, action_type):
        raise NotImplementedError()

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain'] + '_' + client_config['username'] + (client_config.get('member_cid') or '')

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def _connect_client(client_config):
        try:
            member_cid = client_config.get('member_cid')
            if member_cid:
                member_cids = member_cid.split(',')
            else:
                member_cids = [None]
            connections = []
            for member_cid in member_cids:
                connection = CrowdStrikeConnection(domain=client_config['domain'],
                                                   verify_ssl=client_config['verify_ssl'],
                                                   username=client_config['username'],
                                                   password=client_config['apikey'],
                                                   https_proxy=client_config.get('https_proxy'),
                                                   member_cid=member_cid)
                with connection:
                    pass  # check that the connection credentials are valid
                connections.append(connection)
            return connections
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        for connection in client_data:
            with connection:
                yield from connection.get_device_list(self._get_policies, self._get_vulnerabilities)

    @staticmethod
    def _clients_schema():
        """
        The schema the adapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'CrowdStrike Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name / Client ID',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key / Secret',
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
                },
                {
                    'name': 'member_cid',
                    'type': 'string',
                    'title': 'Member CID'
                }
            ],
            'required': [
                'domain',
                'username',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def parse_groups(groups):
        parsed_groups = []
        if groups and isinstance(groups, list):
            for group in groups:
                parsed_groups.append(Group(created_by=group.get('created_by'),
                                           created_timestamp=parse_date(group.get('created_timestamp')),
                                           description=group.get('description'), group_type=group.get('group_type'),
                                           id=group.get('id'), modified_by=group.get('modified_by'),
                                           modified_time=parse_date(group.get('modified_time')),
                                           name=group.get('name')))
        return parsed_groups

    @staticmethod
    def parse_vulnerabilities(vulnerabilities):
        parsed_vulnerabilities = []
        if isinstance(vulnerabilities, list):
            for vulnerability in vulnerabilities:
                vul = SpotlightVulnerability(created_timestamp=parse_date(vulnerability.get('created_timestamp')),
                                             closed_timestamp=parse_date(vulnerability.get('closed_timestamp')),
                                             status=vulnerability.get('status'),
                                             cve_id=vulnerability.get('cve', {}).get('id'),
                                             cve_score=vulnerability.get('cve', {}).get('base_score'),
                                             cve_severity=vulnerability.get('cve', {}).get('severity'),
                                             application_name=vulnerability.get('app', {}).get('product_name_version'),
                                             )
                parsed_vulnerabilities.append(vul)
        return parsed_vulnerabilities

    @staticmethod
    def add_vulnerable_softwares(device: DeviceAdapter,
                                 parsed_vulnerabilities: List[SpotlightVulnerability]):
        """
        Add vulnerable softwares to device data
        :param device: device for adding its softwares
        :param parsed_vulnerabilities: parsed vulnerabilities
        :return: None
        """
        for vul in parsed_vulnerabilities:
            try:
                severity = vul.cve_severity if vul.cve_severity in ['NONE', 'LOW', 'MEDIUM', 'HIGH',
                                                                    'CRITICAL'] else 'NONE'
                device.add_vulnerable_software(cve_id=vul.cve_id,
                                               software_name=vul.application_name,
                                               cve_severity=severity)
            except Exception:
                logger.exception('Error adding vulnerable software')

    @staticmethod
    def parse_policy(policy, settings_type):
        if not policy:
            return None
        parsed_policy = None
        parsed_groups = []
        parsed_prevention_settings = []
        parsed_sensor_update_settings = None
        try:
            groups = policy.get('groups')
            # parse policies groups
            parsed_groups = CrowdStrikeAdapter.parse_groups(groups)

            # parse policies settings
            if settings_type == 'prevention_settings':
                prevention_settings = policy.get('prevention_settings', [])
                for prevention_sett in prevention_settings:
                    settings = prevention_sett.get('settings', [])
                    all_settings = []
                    for sett in settings:
                        val = PolicySettingValue(enabled=sett.get('value').get('enabled')) \
                            if sett.get('value') else None
                        all_settings.append(PolicySettings(id=sett.get('id'), name=sett.get('name'),
                                                           description=sett.get('description'), value=val))
                    parsed_prevention_settings.append(PreventionSettings(
                        name=prevention_sett.get('name'), settings=all_settings))

            elif settings_type == 'sensor_update_settings':
                settings = policy.get('settings')
                if settings:
                    parsed_sensor_update_settings = SensorUpdateSettings(build=settings.get('build'))

            parsed_policy = Policy(name=policy.get('name'),
                                   description=policy.get('decription'),
                                   platform_name=policy.get('platform_name'),
                                   groups=parsed_groups,
                                   enabled=policy.get('enabled'),
                                   created_by=policy.get('created_by'),
                                   created_time=parse_date(policy.get('created_time')),
                                   prevention_settings=parsed_prevention_settings,
                                   sensor_update_settings=parsed_sensor_update_settings)
        except Exception:
            logger.exception('Error getting policy %s', policy.get('id'))
        return parsed_policy

    # pylint: disable=too-many-statements,too-many-branches,too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('device_id')
                if not device_id:
                    continue
                device.id = device_id
                device.add_agent_version(agent=AGENT_NAMES.crowd_strike, version=device_raw.get('agent_version'),
                                         status=device_raw.get('status'))
                device.cs_agent_version = device_raw.get('agent_version')
                mac_address = device_raw.get('mac_address')
                local_ip = device_raw.get('local_ip')
                device.add_ips_and_macs(mac_address, local_ip.split(',') if local_ip is not None else None)
                try:
                    hostname = device_raw.get('hostname')
                    domain = device_raw.get('machine_domain')
                    if isinstance(self.__machine_domain_whitelist, list) \
                            and self.__machine_domain_whitelist and \
                            str(domain).lower() not in self.__machine_domain_whitelist:
                        continue
                    if not is_domain_valid(domain):
                        domain = None
                    device.domain = domain
                    device.hostname = hostname
                except Exception:
                    logger.exception(f'Problem getting hostname for {device_raw}')
                try:
                    device.figure_os((device_raw.get('platform_name') or '') +
                                     (device_raw.get('os_version') or ''))
                    device.os.build = device_raw.get('build_number')
                    try:
                        device.os.major = int(device_raw.get('service_pack_major'))
                        device.os.minor = int(device_raw.get('service_pack_minor'))
                    except Exception:
                        pass

                    try:
                        if device.os.type == 'OS X':
                            device.full_osx_version = \
                                device_raw.get('os_version').split(' ')[-1].strip(')').strip('(') \
                                + '.' + device_raw.get('minor_version')
                    except Exception:
                        pass
                except Exception:
                    logger.exception(f'Problem getting OS for {device_raw}')
                try:
                    device.last_seen = parse_date(device_raw.get('last_seen'))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                try:
                    device.first_seen = parse_date(device_raw.get('first_seen'))
                except Exception:
                    logger.exception(f'Problem getting first seen')
                device.external_ip = device_raw.get('external_ip')
                device.bios_manufacturer = device_raw.get('bios_manufacturer')
                try:
                    device.groups = self.parse_groups(device_raw.get('groups_data'))
                    if self.__group_name_whitelist:
                        found_group = False
                        for group_raw in device_raw.get('groups_data'):
                            if group_raw.get('name') in self.__group_name_whitelist:
                                found_group = True
                        if not found_group:
                            continue
                except Exception:
                    logger.exception(f'Problem getting groups for {device_raw}')
                try:
                    policies = device_raw.get('device_policies')
                    if policies:
                        prevention_pol = policies.get(consts.PolicyTypes.Prevention.value)
                        if prevention_pol:
                            data = prevention_pol.get('data')
                            device.prevention_policy = self.parse_policy(data, 'prevention_settings') if data else None
                        sensor_update_pol = policies.get(consts.PolicyTypes.SensorUpdate.value)
                        if sensor_update_pol:
                            data = sensor_update_pol.get('data')
                            device.sensor_update_policy = self.parse_policy(
                                data, 'sensor_update_settings') if data else None
                        device_raw.pop('device_policies')
                except Exception:
                    logger.exception(f'Problem getting policies at {device_raw}')
                device.system_product_name = device_raw.get('system_product_name')
                vulnerabilities = device_raw.get('vulnerabilities')
                if vulnerabilities:
                    try:
                        parsed_vulnerabilities = self.parse_vulnerabilities(vulnerabilities)
                        self.add_vulnerable_softwares(device, parsed_vulnerabilities)
                        device.spotlight_vulnerabilities = parsed_vulnerabilities
                        device_raw.pop('vulnerabilities')
                    except Exception:
                        logger.exception(f'Problem getting vulnerabilities for {device_raw}')
                try:
                    if len(str(device_raw)) > (12 * (1024 ** 2)):
                        device_raw = str(device_raw)[:(12 * (1024 ** 2))]
                except Exception:
                    logger.exception(f'Problem trimming device raw')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching CrowdStrike Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'get_policies',
                    'title': 'Get devices policies',
                    'type': 'bool'
                },
                {
                    'name': 'get_vulnerabilities',
                    'title': 'Get devices vulnerabilities',
                    'type': 'bool'
                },
                {
                    'name': 'machine_domain_whitelist',
                    'title': 'Machine domain whitelist',
                    'type': 'string'
                },
                {
                    'name': 'group_name_whitelist',
                    'title': 'Group name whitelist',
                    'type': 'string'
                }
            ],
            'required': [
                'get_policies',
                'get_vulnerabilities'
            ],
            'pretty_name': 'CrowdStrike Falcon Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'get_policies': False,
            'get_vulnerabilities': False,
            'machine_domain_whitelist': None,
            'group_name_whitelist': None
        }

    def _on_config_update(self, config):
        self._get_policies = config['get_policies']
        self._get_vulnerabilities = config['get_vulnerabilities']
        self.__machine_domain_whitelist = [x.lower() for x in config.get('machine_domain_whitelist').split(',')] \
            if config.get('machine_domain_whitelist') else None
        self.__group_name_whitelist = config.get('group_name_whitelist').split(',') \
            if config.get('group_name_whitelist') else None
