import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.thycotic_vault.connection import ThycoticVaultConnection
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from thycotic_adapter.client_id import get_client_id
from thycotic_adapter.structures import ThycoticUserInstance

logger = logging.getLogger(f'axonius.{__name__}')


class ThycoticAdapter(AdapterBase):
    class MyUserAdapter(ThycoticUserInstance):
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
        connection = ThycoticVaultConnection(host=client_config.get('domain'),
                                             verify_ssl=client_config.get('verify_ssl'),
                                             https_proxy=client_config.get('https_proxy'),
                                             proxy_username=client_config.get('proxy_username'),
                                             proxy_password=client_config.get('proxy_password'),
                                             username=client_config.get('username'),
                                             password=client_config.get('password'),
                                             port=client_config.get('port'))
        with connection:
            # This function checks if the connection is valid.
            # it is separated because this class is used also for vault and not only for adapter.
            connection.test_adapter_permissions()
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    # pylint: disable=arguments-differ
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema ThycoticAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Thycotic Secret Server URL',
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
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'format': 'port'
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
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'domain',
                'port',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_thycotic_user_fields(user_raw: dict, user: MyUserAdapter):
        try:
            user.domain_id = int_or_none(user_raw.get('domainId'))
            user.enabled = parse_bool_from_raw(user_raw.get('enabled'))
            user.is_application_account = parse_bool_from_raw(user_raw.get('isApplicationAccount'))
            user.login_failures = int_or_none(user_raw.get('loginFailures'))
        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('userName') or '')

            user.user_created = parse_date(user_raw.get('created'))
            user.display_name = user_raw.get('displayName')
            user.mail = user_raw.get('emailAddress')
            user.is_locked = parse_bool_from_raw(user_raw.get('isLockedOut'))
            user.last_logon = parse_date(user_raw.get('lastLogin'))
            user.username = user_raw.get('userName')

            if user_raw.get('enabled') is not None:
                user.account_disabled = not parse_bool_from_raw(user_raw.get('enabled'))

            self._fill_thycotic_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching Thycotic User for {user_raw}')
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
                logger.exception(f'Problem with fetching Thycotic User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
