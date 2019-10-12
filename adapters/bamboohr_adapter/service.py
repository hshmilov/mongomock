import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from bamboohr_adapter.connection import BamboohrConnection
from bamboohr_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class BamboohrAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(UserAdapter):
        preferred_name = Field(str, 'Preferred Name')
        gender = Field(str, 'Gender')
        division = Field(str, 'Division')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability('api.bamboohr.com')

    @staticmethod
    def get_connection(client_config):
        connection = BamboohrConnection(domain='api.bamboohr.com',
                                        url_base_prefix=f'/api/gateway.php/{client_config["subdomain"]}/v1/',
                                        verify_ssl=True,
                                        https_proxy=client_config.get('https_proxy'),
                                        username=client_config['api_key'],
                                        password='x')
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to BambooHR, reason: {0}'.format(str(e))
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
            yield from client_data.get_users()

    @staticmethod
    def _clients_schema():
        """
        The schema BamboohrAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'subdomain',
                    'title': 'BambooHR Subdomain',
                    'type': 'string'
                },
                {
                    'name': 'api_key',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'subdomain',
                'api_key'
            ],
            'type': 'array'
        }

    def _create_user(self, user_raw):
        try:
            user = self._new_user_adapter()
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None

            # Axonius generic stuff
            user.id = user_id + '_' + (user_raw.get('id') or '')
            user.employee_number = user_raw.get('id')
            user.first_name = user_raw.get('firstName')
            user.last_name = user_raw.get('lastName')
            user.display_name = user_raw.get('displayName')
            user.mail = user_raw.get('workEmail')
            user.user_telephone_number = user_raw.get('mobilePhone')
            user.user_title = user_raw.get('jobTitle')
            user.user_department = user_raw.get('department')
            user.image = user_raw.get('photoUrl')

            # Bamboo-specific stuff
            user.preferred_name = user_raw.get('preferredName')
            user.gender = user_raw.get('gender')
            user.division = user_raw.get('division')

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
