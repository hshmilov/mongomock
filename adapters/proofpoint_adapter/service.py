import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.proofpoint.connection import ProofpointConnection
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw
from proofpoint_adapter.client_id import get_client_id
from proofpoint_adapter.structures import ProofpointUserInstance

logger = logging.getLogger(f'axonius.{__name__}')


class ProofpointAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes

    class MyUserAdapter(ProofpointUserInstance):
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
        connection = ProofpointConnection(domain=client_config.get('domain'),
                                          verify_ssl=client_config.get('verify_ssl'),
                                          https_proxy=client_config.get('https_proxy'),
                                          proxy_username=client_config.get('proxy_username'),
                                          proxy_password=client_config.get('proxy_password'),
                                          username=client_config.get('username'),
                                          password=client_config.get('password'),
                                          organization_domain=client_config.get('organization_domain'))
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint: disable=arguments-differ
    def _query_users_by_client(self, client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list(fetch_inactive_users=self.__fetch_inactive_users)

    @staticmethod
    def _clients_schema():
        """
        The schema ProofpointAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
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
                    'name': 'organization_domain',
                    'title': 'Organization Domain',
                    'type': 'string'
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
                'username',
                'password',
                'verify_ssl',
                'organization_domain'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_proofpoint_user_fields(user_raw: dict, user: MyUserAdapter):
        try:
            user.is_active = parse_bool_from_raw(user_raw.get('is_active'))
            user.alias_emails = user_raw.get('alias_emails')
            user.whitelist_senders = user_raw.get('white_list_senders')
            user.blacklist_senders = user_raw.get('black_list_senders')

        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('uid')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('primary_email') or '')

            user.mail = user_raw.get('primary_email')
            user.employee_type = user_raw.get('type')
            user.first_name = user_raw.get('firstname')
            user.last_name = user_raw.get('surname')

            self._fill_proofpoint_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching Proofpoint User for {user_raw}')
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
                logger.exception(f'Problem with fetching Proofpoint User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_inactive_users',
                    'title': 'Fetch inactive users',
                    'type': 'bool'
                }
            ],
            'required': [
                'fetch_inactive_users'
            ],
            'pretty_name': 'Proofpoint Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_inactive_users': False
        }

    def _on_config_update(self, config):
        self.__fetch_inactive_users = parse_bool_from_raw(config.get('fetch_inactive_users')) or False
