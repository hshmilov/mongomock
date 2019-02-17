import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import (convert_ldap_searchpath_to_domain_name,
                                   is_domain_valid)
from sentinelone_adapter import consts
from sentinelone_adapter.connection import SentinelOneConnection

logger = logging.getLogger(f'axonius.{__name__}')


class SentineloneAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        active_state = Field(str, 'Active State')
        public_ip = Field(str, 'Public IP')
        is_active = Field(bool, 'Is Active')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = SentinelOneConnection(domain=client_config['domain'],
                                               https_proxy=client_config.get('https_proxy'),
                                               username=client_config.get('username'),
                                               password=client_config.get('password'),
                                               verify_ssl=client_config['verify_ssl'],
                                               apikey=client_config.get('token'))
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
        Get all devices from a specific SentinelOne domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a SentinelOne connection

        :return: A json with all the attributes returned from the SentinelOne Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema SentinelOneAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Sentinel One Domain',
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
                    'name': 'token',
                    'title': 'API token',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                }
            ],
            'required': [
                'domain',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=R0912,R0915
    def _create_device_v1(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            uuid = device_raw.get('uuid') or ''
            if not device_id:
                logger.warning(f'Bad device with no id {device_raw}')
                return None
            device.id = device_id + '_' + uuid
            device.agent_version = device_raw.get('agent_version')
            is_active = device_raw.get('is_active')
            if is_active and isinstance(is_active, bool):
                device.is_active = is_active
            is_uninstalled = device_raw.get('is_uninstalled')
            if is_uninstalled and isinstance(is_uninstalled, bool):
                logger.warning(f'Uninstalled device, drop it {device_raw}')
                return None
            try:
                device.last_seen = parse_date(device_raw.get('last_active_date'))
            except Exception:
                logger.exception(f'Problem getting last seen at {device_raw}')
            device.public_ip = device_raw.get('external_ip')
            network_information = device_raw.get('network_information') or {}
            if not isinstance(network_information, dict):
                network_information = dict()
            domain = network_information.get('domain')
            if is_domain_valid(domain=domain):
                device.domain = domain
            device.hostname = network_information.get('computer_name')

            software_information = device_raw.get('software_information') or {}
            if not isinstance(software_information, dict):
                software_information = dict()

            device.figure_os((software_information.get('os_name') or '') + ' ' +
                             (software_information.get('os_arch') or ''))

            interfaces = network_information.get('interfaces') or []
            if not isinstance(interfaces, list):
                interfaces = []
            for interface in interfaces:
                try:
                    device.add_nic(interface.get('physical'),
                                   (interface.get('inet6') or []) + (interface.get('inet') or []),
                                   name=interface.get('name'))
                except Exception:
                    logger.exception(f'Problem adding nic {str(interface)} to SentinelOne')

            hardware_information = device_raw.get('hardware_information') or {}
            if not isinstance(hardware_information, dict):
                hardware_information = dict(0)
            try:
                device.total_physical_memory = int((hardware_information.get('total_memory') or 0)) / 1024.0
            except Exception:
                logger.exception(f'Problem with adding memory to {device_raw}')
            try:
                device.last_used_users = (device_raw.get('last_logged_in_user_name') or '').split(',')
                for user_raw in device_raw.get('users') or []:
                    try:
                        device.add_users(username=user_raw.get('name'),
                                         user_sid=user_raw.get('sid'),
                                         last_use_date=parse_date(user_raw.get('login_time')))
                    except Exception:
                        logging.exception(f'Problem getting user for {user_raw}')
            except Exception:
                logging.exception(f'Problem getting users for {device_raw}')
            try:
                apps = device_raw.get('apps')
                if not isinstance(apps, list):
                    apps = []
                for app in apps:
                    try:
                        app_name = app.get('name')
                        app_version = app.get('version')
                        app_vendor = app.get('publisher')
                        device.add_installed_software(name=app_name, version=app_version, vendor=app_vendor)
                    except Exception:
                        logger.exception(f'Problem adding app to device raw {app} device: {device_raw}')
            except Exception:
                logger.exception(f'Problem adding apps to {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Got problems with device {device_raw}')
        return None

    def _create_device_v2(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            computer_name = device_raw.get('computerName') or ''
            if not device_id:
                logger.warning(f'Bad device with no id {device_raw}')
                return None
            device.id = device_id + computer_name
            device.agent_version = device_raw.get('agentVersion')
            try:
                device.last_seen = parse_date(device_raw.get('lastActiveDate'))
            except Exception:
                logger.exception(f'Problem getting last seen at {device_raw}')
            device.public_ip = device_raw.get('externalIp')
            device.domain = device_raw.get('domain')
            ad_domain = ''
            try:
                ad_nodes_names = (device_raw.get('activeDirectory') or {}).get('computerDistinguishedName') or ''
                ad_domain = convert_ldap_searchpath_to_domain_name(ad_nodes_names)
            except Exception:
                logger.exception(f'Problem getting SentinelOne AD info {device_raw}')
            if computer_name:
                hostname = computer_name
                if ad_domain and ad_domain.upper() != 'N/A':
                    hostname = f'{hostname}.{ad_domain}'
                device.hostname = hostname
            device.figure_os((device_raw.get('osType') or '') + ' ' + (device_raw.get('osName') or ''))
            interfaces = device_raw.get('networkInterfaces') or []
            if not isinstance(interfaces, list):
                interfaces = []
            for interface in interfaces:
                try:
                    device.add_nic(interface.get('physical'),
                                   interface.get('inet6', []) + interface.get('inet', []),
                                   name=interface.get('name'))
                except Exception:
                    logger.exception(f'Problem adding nic {str(interface)} to SentinelOne')
            try:
                device.last_used_users = (device_raw.get('lastLoggedInUserName') or '').split(',')
            except Exception:
                logger.exception(f'Problem with adding users to {device_raw}')
            try:
                device.total_physical_memory = int((device_raw.get('totalMemory') or 0)) / 1024.0
            except Exception:
                logger.exception(f'Problem with adding memory to {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Got problems with device {device_raw}')
        return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, api_version in devices_raw_data:
            device = None
            if api_version == consts.V2:
                device = self._create_device_v2(device_raw)
            if api_version == consts.V1:
                device = self._create_device_v1(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
