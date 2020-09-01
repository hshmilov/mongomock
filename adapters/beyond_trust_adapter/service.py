import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.beyond_trust.consts import (BEYOND_TRUST_DATABASE,
                                                 BEYOND_TRUST_HOST,
                                                 BEYOND_TRUST_PORT,
                                                 DEFAULT_BEYOND_TRUST_DATABASE,
                                                 DEFAULT_BEYOND_TRUST_PORT,
                                                 DEFAULT_RECORDS_PER_QUERY,
                                                 DEVICES_FETECHED_AT_A_TIME,
                                                 DEVICES_QUERY, DOMAINS_QUERY,
                                                 PASSWORD, POLICIES_QUERY,
                                                 USER, USER_SESSIONS_QUERY,
                                                 USERS_QUERY)
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.clients.mysql.connection import MySQLConnection
from axonius.clients.rest.connection import RESTConnection
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string, parse_bool_from_raw, int_or_none
from beyond_trust_adapter.client_id import get_client_id
from beyond_trust_adapter.structures import (BeyondTrustDeviceInstance,
                                             BeyondTrustUserInstance,
                                             UserPolicy)

logger = logging.getLogger(f'axonius.{__name__}')


class BeyondTrustAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(BeyondTrustDeviceInstance):
        pass

    class MyUserAdapter(BeyondTrustUserInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(
            client_config.get('server'),
            port=client_config.get('port', DEFAULT_BEYOND_TRUST_PORT)
        )

    def get_connection(self, client_config):
        database = client_config.get(
            BEYOND_TRUST_DATABASE,
            DEFAULT_BEYOND_TRUST_DATABASE
        )

        port = client_config.get(
            BEYOND_TRUST_PORT,
            DEFAULT_BEYOND_TRUST_PORT
        )

        connection = MSSQLConnection(
            database=database,
            server=client_config.get(BEYOND_TRUST_HOST),
            port=port,
            devices_paging=self.__devices_fetched_at_a_time
        )

        connection.set_credentials(
            username=client_config.get(USER),
            password=client_config.get(PASSWORD)
        )

        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except Exception:
            message = f'Error connecting to client host: {client_config.get(BEYOND_TRUST_HOST)}  ' \
                      f'database: {client_config.get(BEYOND_TRUST_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data: MSSQLConnection):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            hosts = client_data.query(DEVICES_QUERY)
            domains = client_data.query(DOMAINS_QUERY)

            # Extend hosts table with columns of domains table.
            hosts = MySQLConnection.left_join_tables(
                left_table=hosts,
                right_table=domains,
                left_comparison_field='DomainID',
                right_comparison_field='DomainID'
            )

            yield from hosts

    # pylint: disable=arguments-differ
    def _query_users_by_client(self, client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            domains = client_data.query(DOMAINS_QUERY)
            users = client_data.query(USERS_QUERY)

            # Extend users table with all relevant columns from other relevant tables.
            users = MySQLConnection.left_join_tables(
                left_table=users,
                right_table=domains,
                left_comparison_field='DomainID',
                right_comparison_field='DomainID'
            )

            del domains  # Release memory of domains object.

            policies = client_data.query(POLICIES_QUERY)
            user_sessions = client_data.query(USER_SESSIONS_QUERY)
            user_sessions = MySQLConnection.left_join_tables(
                left_table=user_sessions,
                right_table=policies,
                left_comparison_field='PolicyID',
                right_comparison_field='PolicyID'
            )

            del policies    # Release memory of policies object.

            users = MySQLConnection.left_join_tables(
                left_table=users,
                right_table=user_sessions,
                left_comparison_field='UserID',
                right_comparison_field='UserID'
            )

            del user_sessions   # Release memory of user sessions object.

            yield from users

    def _clients_schema(self):
        """
        The schema BeyondTrustAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': BEYOND_TRUST_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': BEYOND_TRUST_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': DEFAULT_BEYOND_TRUST_PORT,
                    'format': 'port'
                },
                {
                    'name': BEYOND_TRUST_DATABASE,
                    'title': 'Database',
                    'type': 'string',
                    'default': DEFAULT_BEYOND_TRUST_DATABASE
                },
                {
                    'name': USER,
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                BEYOND_TRUST_HOST,
                BEYOND_TRUST_PORT,
                USER,
                PASSWORD,
                BEYOND_TRUST_DATABASE
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_beyond_trust_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.domain_id = device_raw.get('DomainID')
            device.host_sid = device_raw.get('HostSID')
            device.name_netbios = device_raw.get('NameNETBIOS')
            device.chassis_type = device_raw.get('ChassisType')
            device.os_product_type = device_raw.get('OSProductType')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('HostID')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            domain_id = device_raw.get('DomainID')
            device.id = str(device_id) + '_' + (str(domain_id) or '')
            device.hostname = device_raw.get('HostName')
            device.domain = device_raw.get('DomainName')
            device.uptime = int_or_none(device_raw.get('SystemUptime'))

            platform_type = device_raw.get('PlatformType')
            os = device_raw.get('OS')

            device.figure_os(f'{platform_type} {os}')
            self._fill_beyond_trust_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching BeyondTrust Device for {device_raw}')
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
                logger.exception(f'Problem with fetching BeyondTrust Device for {device_raw}')

    @staticmethod
    def _fill_beyond_trust_user_fields(user_raw: dict, user: MyUserAdapter):
        try:
            user.domain_id = user_raw.get('DomainID')
            user.last_logon_id = user_raw.get('LogonID')
            user.is_power_user = parse_bool_from_raw(user_raw.get('IsPowerUser'))
            user.ui_language = user_raw.get('UILanguage')
            user.locale = user_raw.get('Locale')
            user.last_used_host_id = user_raw.get('HostID')
            user.policy = UserPolicy(
                id=user_raw.get('PolicyID'),
                guid=user_raw.get('PolicyGUID'),
                name=user_raw.get('PolicyName'),
                description=user_raw.get('Description'),
                platform_type=user_raw.get('PlatformType')
            )
        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('UserID')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None

            domain_id = user_raw.get('DomainID')
            user.id = str(user_id) + '_' + (str(domain_id) or '')
            user.username = user_raw.get('UserName')
            user.user_sid = user_raw.get('UserSID')
            user.domain = user_raw.get('DomainName')
            user.last_logon = parse_date(user_raw.get('LogonTime'))
            user.last_logoff = parse_date(user_raw.get('LogoffTime'))
            user.is_admin = parse_bool_from_raw(user_raw.get('IsAdmin'))

            self._fill_beyond_trust_user_fields(user_raw, user)
            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching BeyondTrust User for {user_raw}')
            return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        """
        Gets raw data and yields User objects.
        :param users_raw_data: the raw data we get.
        :return:
        """
        for user_raw in users_raw_data:
            if not user_raw:
                continue
            try:
                # noinspection PyTypeChecker
                user = self._create_user(user_raw, self._new_user_adapter())
                if user:
                    yield user
            except Exception:
                logger.exception(f'Problem with fetching BeyondTrust User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': DEVICES_FETECHED_AT_A_TIME,
                    'type': 'integer',
                    'title': 'SQL pagination'
                }
            ],
            'required': [DEVICES_FETECHED_AT_A_TIME],
            'pretty_name': 'BeyondTrust Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            DEVICES_FETECHED_AT_A_TIME: DEFAULT_RECORDS_PER_QUERY
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config[DEVICES_FETECHED_AT_A_TIME]
