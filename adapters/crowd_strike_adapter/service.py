import datetime
import logging

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


class CrowdStrikeAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        external_ip = Field(str, 'External IP')
        groups = ListField(Group, 'Groups')
        prevention_policy = Field(Policy, 'Prevention Policy')
        sensor_update_policy = Field(Policy, 'Sensor Update Policy')
        cs_agent_version = Field(str, 'CrowdStrike Agent Version')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def action(self, action_type):
        raise NotImplementedError()

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain'] + '_' + client_config['username']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            connection = CrowdStrikeConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                               username=client_config['username'], password=client_config['apikey'],
                                               https_proxy=client_config.get('https_proxy'))
            with connection:
                pass  # check that the connection credentials are valid
            return connection
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
        with client_data:
            yield from client_data.get_device_list(self._get_policies)

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

    # pylint: disable=too-many-statements
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('device_id')
                if not device_id:
                    continue
                device.id = device_id
                device.add_agent_version(agent=AGENT_NAMES.crowd_strike, version=device_raw.get('agent_version'))
                device.cs_agent_version = device_raw.get('agent_version')
                mac_address = device_raw.get('mac_address')
                local_ip = device_raw.get('local_ip')
                device.add_ips_and_macs(mac_address, local_ip.split(',') if local_ip is not None else None)
                try:
                    hostname = device_raw.get('hostname')
                    domain = device_raw.get('machine_domain')
                    if not is_domain_valid(domain):
                        domain = None
                    device.domain = domain
                    device.hostname = hostname
                except Exception:
                    logger.exception(f'Problem getting hostname for {device_raw}')
                try:
                    device.figure_os((device_raw.get('platform_name') or '') +
                                     (device_raw.get('os_version') or ''))
                    device.os.distribution = device_raw.get('os_version')
                except Exception:
                    logger.exception(f'Problem getting OS for {device_raw}')
                try:
                    device.last_seen = parse_date(device_raw.get('last_seen'))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                device.external_ip = device_raw.get('external_ip')
                device.device_manufacturer = device_raw.get('bios_manufacturer')
                try:
                    device.groups = self.parse_groups(device_raw.get('groups_data'))
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
                    'title': 'Get Devices Policies',
                    'type': 'bool'
                }
            ],
            'required': [
                'get_policies'
            ],
            'pretty_name': 'Crowdstrike Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'get_policies': False
        }

    def _on_config_update(self, config):
        self._get_policies = config['get_policies']
