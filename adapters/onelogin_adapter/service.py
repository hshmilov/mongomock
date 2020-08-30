import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.onelogin.connection import OneloginConnection
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import int_or_none
from onelogin_adapter.client_id import get_client_id
from onelogin_adapter.structures import OneloginUserInstance

logger = logging.getLogger(f'axonius.{__name__}')


class OneloginAdapter(AdapterBase):
    class MyUserAdapter(OneloginUserInstance):
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
        connection = OneloginConnection(domain=client_config.get('domain'),
                                        verify_ssl=client_config.get('verify_ssl'),
                                        https_proxy=client_config.get('https_proxy'),
                                        proxy_username=client_config.get('proxy_username'),
                                        proxy_password=client_config.get('proxy_password'),
                                        client_id=client_config.get('client_id'),
                                        client_secret=client_config.get('client_secret'))
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
        The schema OneloginAdapter expects from configs

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
                    'name': 'client_id',
                    'title': 'Client ID',
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
                'client_id',
                'client_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_onelogin_user_fields(user_raw: dict, user: MyUserAdapter):
        try:
            user.activated_at = parse_date(user_raw.get('activated_at'))
            user.directory_id = user_raw.get('directory_id')
            user.distinguished_name = user_raw.get('distinguished_name')
            user.external_id = user_raw.get('external_id')
            user.group_id = int_or_none(user_raw.get('group_id'))
            user.invalid_login_attempts = int_or_none(user_raw.get('invalid_login_attempts'))
            user.invitation_sent_at = parse_date(user_raw.get('invitation_sent_at'))
            user.locked_until = parse_date(user_raw.get('locked_until'))
            user.sam_account_name = user_raw.get('samaccountname')
            user.state = int_or_none(user_raw.get('state'))
            user.manager_user_id = int_or_none(user_raw.get('manager_user_id'))
            user.manager_ad_id = int_or_none(user_raw.get('manager_ad_id'))
            user.preferred_locale_code = user_raw.get('preferred_locale_code')
            user.role_ids = user_raw.get('role_id')
            user.trusted_idp_id = int_or_none(user_raw.get('trusted_idp_id'))
            user.comment = user_raw.get('comment')
            user.company = user_raw.get('company')
            user.user_principal_name = user_raw.get('userprincipalname')
            user.locale_code = user_raw.get('locale_code')
            user.openid_name = user_raw.get('openid_name')
            user.notes = user_raw.get('notes')

        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('email') or '')
            user.mail = user_raw.get('email')
            user.first_name = user_raw.get('firstname')
            user.last_name = user_raw.get('lastname')
            user.user_telephone_number = user_raw.get('phone')
            user.last_seen = parse_date(user_raw.get('updated_at'))
            user.username = user_raw.get('username')
            user.last_password_change = parse_date(user_raw.get('password_changed_at'))
            user.user_status = int_or_none(user_raw.get('status'))
            user.user_created = parse_date(user_raw.get('created_at'))
            user.user_department = user_raw.get('department')
            user.user_title = user_raw.get('title')
            user.last_logon = parse_date(user_raw.get('last_login'))

            member_of = user_raw.get('member_of')
            if isinstance(member_of, str):
                member_of = [member_of]
            user.groups = member_of

            if isinstance(user_raw.get('apps'), list):
                for app in user_raw.get('apps'):
                    if not isinstance(app, dict):
                        continue
                    user.add_user_application(app_name=app.get('name'))

            self._fill_onelogin_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching Onelogin User for {user_raw}')
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
                logger.exception(f'Problem with fetching Onelogin User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
