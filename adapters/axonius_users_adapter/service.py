import logging

from typing import Optional

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius_users_adapter.connection import AxoniusUsersConnection
from axonius_users_adapter.client_id import get_client_id
from axonius_users_adapter.structures import SystemUser, PermissionV2, Role, PermissionV1

logger = logging.getLogger(f'axonius.{__name__}')


class AxoniusUsersAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(SystemUser):
        pass

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
    def get_connection(client_config):
        connection = AxoniusUsersConnection(domain=client_config['domain'],
                                            verify_ssl=client_config['verify_ssl'],
                                            https_proxy=client_config.get('https_proxy'),
                                            apikey=client_config['apikey'],
                                            api_secret=client_config['api_secret'])
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
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema AxoniusUsersAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Axonius Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string'
                },
                {
                    'name': 'api_secret',
                    'title': 'API Secret',
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
                'apikey',
                'api_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _is_valid_action_item(action_name, is_permitted):
        return isinstance(action_name, str) and isinstance(is_permitted, bool)

    def _parse_user_role(self, user_role: Optional[dict]):
        if not (isinstance(user_role, dict) and isinstance(user_role.get('permissions'), dict)):
            logger.error(f'Invalid user_roles_raw given: {user_role}')
            return None

        role_permissions = []
        for category_name, category in user_role['permissions'].items():
            if not isinstance(category, dict):
                continue

            for section_or_action_name, val in category.items():
                section_name = None

                #  * action_item = 'action_name': bool , e.g. "get": true
                if self._is_valid_action_item(section_or_action_name, val):
                    actions = {section_or_action_name:  val}
                #  * 'section_name': { action_item, action_item, ... }
                #    e.g. "connections": { "delete": true, "post": true, "put": true }
                elif (isinstance(val, dict) and
                      all(self._is_valid_action_item(k, v)
                          for k, v in val.items())):
                    section_name = section_or_action_name
                    actions = val
                else:
                    logger.warning(f'invalid permission value found for'
                                   f' {category_name}.{section_or_action_name}: {val}')
                    continue

                for action_name, is_permitted in actions.items():
                    try:
                        role_permissions.append(PermissionV2(category=category_name,
                                                             section=section_name,
                                                             action=action_name,
                                                             is_permitted=is_permitted))
                    except Exception:
                        logger.exception(f'Failed appending role permission'
                                         f' {category_name};{section_name};{action_name}: {is_permitted}')

        try:
            return Role(uuid=user_role.get('uuid'),
                        name=user_role.get('name'),
                        date_fetched=parse_date(user_role.get('date_fetched')),
                        predefined=user_role.get('predefined'),
                        permissions=role_permissions)
        except Exception:
            logger.exception(f'Failed constructing role: {user_role}')
            return None

    def _create_user(self, user_raw):
        try:
            # noinspection PyTypeChecker
            user = self._new_user_adapter()  # type: AxoniusUsersAdapter.MyUserAdapter
            user_id = user_raw.get('uuid')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = user_id

            # generic fields
            user.username = user_raw.get('user_name')
            user.first_name = user_raw.get('first_name')
            user.last_name = user_raw.get('last_name')
            user.image = user_raw.get('pic_name')
            user.is_admin = user_raw.get('admin')
            user.last_logon = parse_date(user_raw.get('last_login'))

            # specific fields
            user.source = user_raw.get('source')
            user.role_name = user_raw.get('role_name')

            # old permissions (pre 3.3)
            permissions_raw = user_raw.get('permissions')
            if isinstance(permissions_raw, dict):
                permissions = []
                for permission_type, permission_level in permissions_raw.items():
                    try:
                        permissions.append(PermissionV1(type=permission_type,
                                                        level=permission_level))
                    except Exception:
                        logger.warning(f'Invalid permission encountered: {permission_type} {permission_level}')
                user.permissions = permissions

            # new role permissions (post 3.3)
            user.role = self._parse_user_role(user_raw.get('role'))

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching BambooHR user for {user_raw}')
            return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        for user_raw in users_raw_data:
            user = self._create_user(user_raw)
            if user:
                yield user

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
