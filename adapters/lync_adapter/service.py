import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.lync.connection import LyncConnection
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.utils.files import get_local_config_file
from lync_adapter.client_id import get_client_id
from lync_adapter.structures import LyncUserInstance

logger = logging.getLogger(f'axonius.{__name__}')


class LyncAdapter(AdapterBase):
    class MyUserAdapter(LyncUserInstance):
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
        connection = LyncConnection(domain=client_config.get('domain'),
                                    verify_ssl=client_config.get('verify_ssl'),
                                    https_proxy=client_config.get('https_proxy'),
                                    proxy_username=client_config.get('proxy_username'),
                                    proxy_password=client_config.get('proxy_password'),
                                    username=client_config.get('username'),
                                    password=client_config.get('password'))
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
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

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
        The schema LyncAdapter expects from configs

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
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_lync_user_fields(user_raw: dict, user: MyUserAdapter):
        try:
            if isinstance(user_raw.get('emailAddresses'), list):
                user.email_addresses = user_raw.get('emailAddresses')
            user.mobile_phone_number = user_raw.get('mobilePhoneNumber')
            user.office_phone_number = user_raw.get('office')
            user.other_phone_number = user_raw.get('otherPhoneNumber')
            user.work_phone_number = user_raw.get('workPhoneNumber')
        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            if isinstance(user_raw.get('emailAddresses'), list):
                user_id = user_raw.get('emailAddresses')[0]
            else:
                user_id = user_raw.get('emailAddresses')

            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id)

            user.organizational_unit = user_raw.get('company')
            user.user_department = user_raw.get('department')
            user.mail = user_id

            user.user_telephone_number = user_raw.get('homePhoneNumber')
            user.display_name = user_raw.get('name')
            user.user_title = user_raw.get('title')
            user.employee_type = user_raw.get('type')

            self._fill_lync_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching Lync User for {user_raw}')
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
                logger.exception(f'Problem with fetching Lync User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
