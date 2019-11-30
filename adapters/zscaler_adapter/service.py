import logging
import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.users.user_adapter import UserAdapter
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from zscaler_adapter.connection import ZscalerConnection
from zscaler_adapter.client_id import get_client_id
from zscaler_adapter.consts import DEFAULT_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class ZscalerAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        company_name = Field(str, 'Company Name')
        detail = Field(str, 'Detail')
        registration_state = Field(str, 'Registration State')
        policy_name = Field(str, 'Policy Name')
        owner = Field(str, 'Owner')

    class MyUserAdapter(UserAdapter):
        comments = Field(str, 'Comments')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _get_domain(client_config):
        return client_config.get('domain') or DEFAULT_DOMAIN

    @staticmethod
    def _test_reachability(client_config):
        domain = ZscalerAdapter._get_domain(client_config)
        return RESTConnection.test_reachability(domain)

    @staticmethod
    def get_connection(client_config):
        connection = ZscalerConnection(domain=ZscalerAdapter._get_domain(client_config),
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       username=client_config['username'],
                                       password=client_config['password'],
                                       rest_apikey=client_config.get('apikey'))
        with connection:
            connection.connect_zapi()
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            domain = self._get_domain(client_config)
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(domain, str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        duplicated_macs_list = []
        with client_data:
            client_data.connect_zapi()
            if self.__ignore_macs_dups:
                macs_list = []
                for device_raw in client_data.get_device_list():
                    mac = device_raw.get('macAddress')
                    if mac:
                        if mac in macs_list:
                            duplicated_macs_list.append(mac)
                        else:
                            macs_list.append(mac)
            for device_raw in client_data.get_device_list():
                yield device_raw, duplicated_macs_list

    @staticmethod
    def _clients_schema():
        """
        The schema ZscalerAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Zscaler Domain',
                    'type': 'string',
                    'default': DEFAULT_DOMAIN,
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
                    'name': 'apikey',
                    'title': 'API Key',
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
    def _create_device(device, device_raw, duplicated_macs_list=None):
        if not device_raw.get('id'):
            logger.warning(f'Bad device with no ID {device_raw}')
            return None

        device.id = 'zscaler_' + str(device_raw.get('id'))

        if device_raw.get('machineHostname'):
            device.id = device.id + '_' + device_raw['machineHostname']

        mac = device_raw.get('macAddress')
        if not duplicated_macs_list or (mac and mac not in duplicated_macs_list):
            device.add_nic(mac=mac)
        device.figure_os(device_raw.get('osVersion'))

        # Sometimes Zscaler return 'disabled' instead of hostname
        hostname = device_raw.get('machineHostname') or ''
        if hostname.lower() != 'disabled':
            device.hostname = hostname

        device.device_manufacturer = device_raw.get('manufacturer')

        try:
            timestamp = device_raw.get('last_seen_time')
            if timestamp:
                device.last_seen = datetime.datetime.fromtimestamp(int(timestamp))
        except Exception:
            logger.exception('Failed to set last seen')

        if device_raw.get('user'):
            device.last_used_users.append(device_raw.get('user'))

        device.policy_name = device_raw.get('policyName')
        device.owner = device_raw.get('owner')
        device.company_name = device_raw.get('companyName')
        device.detail = device_raw.get('detail')
        device.set_raw(device_raw)
        return device

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, duplicated_macs_list in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device = self._create_device(device, device_raw, duplicated_macs_list)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Zscaler Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'ignore_macs_dups',
                    'title': 'Ignore Duplicated Macs',
                    'type': 'bool'
                }
            ],
            'required': [
                'ignore_macs_dups'
            ],
            'pretty_name': 'Zscaler Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'ignore_macs_dups': False
        }

    def _on_config_update(self, config):
        self.__ignore_macs_dups = config['ignore_macs_dups']

    # pylint: disable=arguments-differ
    @staticmethod
    def _query_users_by_client(key, data):
        with data:
            data.connect_api()
            yield from data.get_user_list()

    def _create_user(self, user_raw):
        try:
            user = self._new_user_adapter()
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('name') or '')
            user.username = user_raw.get('name')
            user.mail = user_raw.get('email')
            try:
                groups_raw = user_raw.get('groups') if isinstance(user_raw.get('groups'), list) else []
                for group_raw in groups_raw:
                    if isinstance(group_raw, dict) and group_raw.get('name'):
                        user.groups.append(group_raw.get('name'))
            except Exception:
                logger.exception(f'Problem with group for {user_raw}')
            department_raw = user_raw.get('department')
            if not isinstance(department_raw, dict):
                department_raw = {}
            user.user_department = department_raw.get('name')
            user.comments = user_raw.get('comments')
            if isinstance(user_raw.get('adminUser'), bool):
                user.is_admin = user_raw.get('adminUser')
            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching BambooHR user for {user_raw}')
            return None

    def _parse_users_raw_data(self, users_raw_data):
        for user_raw in users_raw_data:
            user = self._create_user(user_raw)
            if user:
                yield user
