import logging

from axonius.users.user_adapter import UserAdapter

from axonius.fields import Field, ListField

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from men_and_mice_adapter.connection import MenAndMiceConnection
from men_and_mice_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class MenAndMiceAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        pass
    # pylint: disable=too-many-instance-attributes

    class MyUserAdapter(UserAdapter):
        ref = Field(str, 'Ref', description='API Reference ID')
        auth_type = Field(str, 'Authentication Type')
        roles = ListField(str, 'Roles', description='The roles the user is directly associated to')
        group_roles = ListField(str, 'Group Roles', description='The roles the user has through his group membership')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return MenAndMiceConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = MenAndMiceConnection(domain=client_config['domain'],
                                          verify_ssl=client_config['verify_ssl'],
                                          https_proxy=client_config.get('https_proxy'),
                                          username=client_config['username'],
                                          password=client_config['password'])
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

    # pylint: disable=arguments-differ
    @staticmethod
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_users()

    @staticmethod
    def _clients_schema():
        """
        The schema MenAndMiceAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'MenAndMice Domain',
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

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('name')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            # Generic Axonius stuff
            device.id = device_id + '_' + str(device_raw.get('ref') or '')
            device.name = device_raw.get('name') or f'UNNAMED_{device_id}'
            ifaces = device_raw.get('interfaces') or []
            for iface in ifaces:
                try:
                    device.add_nic(
                        mac=iface.get('clientIdentifier'),
                        ips=iface.get('addresses'),
                        name=iface.get('name')
                    )
                except Exception as e:
                    logger.info(f'Failed to add nic for device {device.id}. '
                                f'raw info: {iface}. The error was: {str(e)}')
            # M&M Specific stuff
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Men&Mice Device for {device_raw}')
            return None

    @staticmethod
    def _extract_list(raw_list: list, target_field: str='name'):
        result = list()
        if not isinstance(raw_list, list):
            return []
        for item_raw in raw_list:
            if isinstance(item_raw, dict) and item_raw.get(target_field):
                result.append(item_raw.get(target_field))
            else:
                logger.warning(f'Failed to add {item_raw} from {raw_list}: value type mismatch')
        return result

    def _create_user(self, user_raw):
        try:
            user = self._new_user_adapter()
            user_id = user_raw.get('name')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            # Axonius generic stuff
            user.id = user_id + '_' + str(user_raw.get('ref') or '')
            user.username = user_raw['name']
            user.display_name = user_raw.get('fullName')
            user.description = user_raw.get('description')
            user.mail = user_raw.get('email')
            # M&M-Specific stuff
            user.auth_type = user_raw.get('authenticationType')
            user.ref = user_raw.get('ref')
            roles_raw = user_raw.get('roles')
            try:
                user.roles = self._extract_list(roles_raw)
            except Exception as e:
                logger.warning(f'Could not fetch roles for {user_raw}: {str(e)}')
            groups_raw = user_raw.get('groups')
            try:
                user.groups = self._extract_list(groups_raw)
            except Exception as e:
                logger.warning(f'Could not fetch groups for {user_raw}: {str(e)}')
            group_roles_raw = user_raw.get('groupRoles')
            try:
                user.group_roles = self._extract_list(group_roles_raw)
            except Exception as e:
                logger.warning(f'Could not fetch group roles for {user_raw}: {str(e)}')
            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem fetching Men&Mice user for {user_raw}')
            return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        for user_raw in users_raw_data:
            user = self._create_user(user_raw)
            if user:
                yield user

    # pylint: disable=arguments-differ
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Network, AdapterProperty.UserManagement]
