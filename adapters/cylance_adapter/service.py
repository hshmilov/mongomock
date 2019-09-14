import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import is_hostname_valid
from cylance_adapter.connection import CylanceConnection

logger = logging.getLogger(f'axonius.{__name__}')


class CylanceAdapter(AdapterBase):

    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        is_safe = Field(str, 'Is Safe')
        device_state = Field(str, 'Device State', enum=['Online', 'Offline'])
        policy_id = Field(str, 'Policy ID')
        policy_name = Field(str, 'Policy Name')
        policies_details = ListField(str, 'Policies Details')
        tenant_tag = Field(str, 'Tenant Tag')
        agent_version = Field(str, 'Cylance Agent Version')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain'] + '_' + client_config['tid'] + '_' + client_config['app_id']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            connection = CylanceConnection(domain=client_config['domain'],
                                           app_id=client_config['app_id'], app_secret=client_config['app_secret'],
                                           tid=client_config['tid'], https_proxy=client_config.get('https_proxy'))
            with connection:
                pass  # check that the connection credentials are valid
            return connection, client_config.get('tenant_tag')
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific Cylance domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Cylance connection

        :return: A json with all the attributes returned from the Cylance Server
        """
        connection, tenant_tag = client_data
        with connection:
            for device_raw in connection.get_device_list():
                yield device_raw, tenant_tag

    @staticmethod
    def _clients_schema():
        """
        The schema CylanceAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Cylance Domain',
                    'type': 'string'
                },
                {
                    'name': 'app_id',
                    'title': 'Application Id',
                    'type': 'string'
                },
                {
                    'name': 'app_secret',
                    'title': 'Application Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'tid',
                    'title': 'Tenant API Key',
                    'type': 'string'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'tenant_tag',
                    'title': 'Tenant Tag',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'app_id',
                'app_secret',
                'tid'
            ],
            'type': 'array'
        }

    # pylint: disable=R1702,R0912,R0915
    def _create_device(self, device_raw, policies_dict, tenant_tag):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if not device_id:
                logger.warning(f'No id of device {device_raw}')
                return None
            device.id = device_id + (device_raw.get('host_name') or '')
            device.tenant_tag = tenant_tag
            device.figure_os((device_raw.get('operatingSystem') or '') + ' ' + (device_raw.get('os_version') or ''))
            hostname = device_raw.get('host_name') or ''
            if not hostname and not device_raw.get('agent_version') and device_raw.get('state') == 'Offline':
                logger.warning(f'This is not a real device {device_raw}')
                return None
            if not is_hostname_valid(hostname):
                hostname = ''
            try:
                # Special condition to OS X
                device_os = device.os
                if device_os:
                    if device_os.type == 'OS X':
                        try:
                            host_no_spaces_list = device_raw.get('name').replace(' ', '-').split('-')
                            host_no_spaces_list[0] = ''.join(char for char in host_no_spaces_list[0] if char.isalnum())
                            if len(host_no_spaces_list) > 1:
                                host_no_spaces_list[1] = ''.join(
                                    char for char in host_no_spaces_list[1] if char.isalnum())
                            hostname = '-'.join(host_no_spaces_list).split('.')[0]
                        except Exception:
                            logger.exception(f'Problem with OS X hostname logic for {device_raw}')
            except Exception:
                logger.debug(f'Problem in MAX OS hostname parsing for {device_raw}')
            if len(hostname) > 0:
                device.hostname = hostname
            try:
                if hostname and 'workgroup' not in hostname.lower() and 'local' not in hostname.lower():
                    device.domain = '.'.join(hostname.split('.')[1:])
            except Exception:
                logger.exception(f'Problem getting domain in {device_raw}')
            device.name = device_raw.get('name')
            try:
                mac_addresses = device_raw.get('mac_addresses') or []
                ip_addresses = device_raw.get('ip_addresses') or []
                device.add_ips_and_macs(mac_addresses, ip_addresses)
            except Exception:
                logger.exception(f'Problem with adding nic to Cylance device {device_raw}')
            device.add_agent_version(agent=AGENT_NAMES.cylance, version=device_raw.get('agent_version', ''))
            device.agent_version = device_raw.get('agent_version')
            try:
                if device_raw.get('date_offline'):
                    device.last_seen = parse_date(str(device_raw.get('date_offline')))
                elif device_raw.get('state') == 'Online':
                    device.last_seen = datetime.datetime.now()
            except Exception:
                logger.exception(f'Problem getting last seen for {device_raw}')
            is_safe_raw = device_raw.get('is_safe')
            if is_safe_raw is not None and is_safe_raw != '':
                device.is_safe = str(is_safe_raw)
            if isinstance(device_raw.get('last_logged_in_user'), str) and device_raw.get('last_logged_in_user'):
                device.last_used_users = device_raw.get('last_logged_in_user').split(',')
            device.device_state = str(device_raw.get('state'))

            try:
                policy_id = (device_raw.get('policy') or {}).get('id')
                device.policy_id = policy_id
                policy_name = (device_raw.get('policy') or {}).get('name')
                device.policy_name = policy_name
                if policy_id and policies_dict.get(policy_id):
                    policy_raw = policies_dict.get(policy_id)
                    if isinstance(policy_raw.get('policy'), list):
                        device_raw['policy_full'] = policy_raw
                        for policy_detail in policy_raw.get('policy'):
                            try:
                                detail_name = policy_detail.get('name')
                                detail_value = policy_detail.get('value')
                                device.policies_details.append(f'{detail_name}:{detail_value}')
                            except Exception:
                                logger.exception(f'Problem getting policy detail {policy_detail}')
            except Exception:
                logger.exception(f'Problem getting policy info for {device_raw}')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Cylance Device {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw_data, tenant_tag in devices_raw_data:
            device_raw, policies_dict = device_raw_data
            device = self._create_device(device_raw, policies_dict, tenant_tag)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
