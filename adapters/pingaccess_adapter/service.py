import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from pingaccess_adapter.connection import PingaccessConnection
from pingaccess_adapter.client_id import get_client_id
from pingaccess_adapter.structures import PingaccessUserInstance

logger = logging.getLogger(f'axonius.{__name__}')


class PingaccessAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(PingaccessUserInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('company_domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = PingaccessConnection(company_domain=client_config['company_domain'],
                                          verify_ssl=client_config['verify_ssl'],
                                          https_proxy=client_config.get('https_proxy'),
                                          client_id=client_config['client_id'],
                                          client_secret=client_config['client_secret'])
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

    @staticmethod
    # pylint: disable=arguments-differ
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
        The schema PingaccessAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'company_domain',
                    'title': 'Pingaccess Company Domain',
                    'type': 'string'
                },
                {
                    'name': 'client_id',
                    'title': 'Client Id',
                    'type': 'string'
                },
                {
                    'name': 'client_secret',
                    'title': 'Client Secret',
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
                'company_domain',
                'client_id',
                'client_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_pingaccess_user_fields(user_raw: dict, user: MyUserAdapter):
        try:
            user.device_type = user_raw.get('deviceType')
            user.device_count = user_raw.get('deviceCount') if isinstance(user_raw.get('deviceCount'), int) else None
            user.device_pairing_date = parse_date(user_raw.get('devicePairingDate'))
            user.device_role = user_raw.get('deviceRole')
            user.device_model = user_raw.get('deviceModel')
            user.os_version = user_raw.get('osVersion')
            user.app_version = user_raw.get('appVersion')
            user.country_code = user_raw.get('countryCode')
            user.user_telephone_number = user_raw.get('phoneNumber')
        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('username')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = user_id + '_' + (user_raw.get('orgEmail') or '')
            user.mail = user_raw.get('orgEmail')
            user.username = user_raw.get('username')
            user.user_status = user_raw.get('status')
            user.user_created = parse_date(user_raw.get('userCreationTime'))

            self._fill_pingaccess_user_fields(user_raw, user)

            user.set_raw(user_raw)

            return user
        except Exception:
            logger.exception(f'Problem with fetching Pingaccess User for {user_raw}')
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
                logger.exception(f'Problem with fetching Pingaccess User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
