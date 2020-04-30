import logging

from axonius.users.user_adapter import UserAdapter
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from workday_adapter.connection import WorkdayConnection
from workday_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class WorkdayAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(UserAdapter):
        # AUTOADAPTER - add here device fields if needed
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
        connection = WorkdayConnection(domain=client_config['domain'],
                                       tenant=client_config['tenant'],
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

    # pylint:disable=arguments-differ
    @staticmethod
    def _query_users_by_client(key, data):
        with data:
            yield from data.get_users_list()

    @staticmethod
    def _clients_schema():
        """
        The schema WorkdayAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Workday Domain',
                    'description': 'Example: https://MY_INSTANCE.workday.com',
                    'type': 'string'
                },
                {
                    'name': 'tenant',
                    'title': 'Workday Tenant Name',
                    'type': 'string'
                },
                # {
                #     'name': 'version',
                #     'title': 'Workday "Human Resources" API version',
                #     'description': 'Example: v34.0',
                #     'type': 'string',
                #     'default': 'v24.1'
                # },
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
                    'name': 'priavte_key',
                    'title': 'Private Key File',
                    'type': 'file'
                },
                {
                    'name': 'public_cert',
                    'title': 'Public Certificate File',
                    'type': 'file',
                    'format': 'password'
                },
                {
                    'name': 'cert_passphrase',
                    'title': 'Certificate Passphrase',
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
                'tenant',
                'username',
                'password',
                'verify_ssl'
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
            user.id = user_id
            user.employee_number = user_raw.get('id')
            user.first_name = user_raw.get('firstName')
            user.last_name = user_raw.get('lastName')
            user.display_name = user_raw.get('displayName')
            user.mail = user_raw.get('workEmail')
            user.user_telephone_number = user_raw.get('mobilePhone')
            user.user_title = user_raw.get('jobTitle')
            user.user_department = user_raw.get('department')
            user.image = user_raw.get('photoUrl')

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching Workday Worker for {user_raw}')
            return None

    def _parse_users_raw_data(self, users_raw):
        for user_raw in users_raw:
            user = self._create_user(user_raw)
            if user:
                yield user

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
