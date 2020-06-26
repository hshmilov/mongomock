import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from beyond_trust_privileged_identity_adapter.consts import AuthenticationMethods, DOMAIN_ACCOUNTS
from beyond_trust_privileged_identity_adapter.connection import BeyondTrustPrivilegedIdentityConnection
from beyond_trust_privileged_identity_adapter.client_id import get_client_id
from beyond_trust_privileged_identity_adapter.structures import BeyondTrustPrivilegedIdentityUserInstance

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class BeyondTrustPrivilegedIdentityAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(BeyondTrustPrivilegedIdentityUserInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _parse_bool(value):
        if isinstance(value, bool):
            return value
        return None

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = BeyondTrustPrivilegedIdentityConnection(domain=client_config['domain'],
                                                             login_type=client_config['login_type'],
                                                             verify_ssl=client_config['verify_ssl'],
                                                             https_proxy=client_config.get('https_proxy'),
                                                             username=client_config['username'],
                                                             password=client_config['password'])
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
        Get all devices from a specific  domain

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
        The schema BeyondTrustPrivilegedIdentityAdapter expects from configs

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
                    'name': 'login_type',
                    'title': 'Login Type',
                    'type': 'string',
                    'enum': [login_type.value for login_type in AuthenticationMethods]
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
                'login_type',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _fill_beyond_trust_privileged_identity_user_fields(self, user_raw: dict, user: MyUserAdapter):
        try:
            user.alert_on_recovery = self._parse_bool(user_raw.get('AlertOnRecovery'))
            user.alert_on_request = self._parse_bool(user_raw.get('AlertOnRequest'))
            user.domain_account = DOMAIN_ACCOUNTS.get(user_raw.get('IsDomainAccount'))
            user.permission_access_remote_sessions = self._parse_bool(user_raw.get('PermissionAccessRemoteSessions'))
            user.permission_add_passwords_for_managed_systems = self._parse_bool(
                user_raw.get('PermissionAddPasswordsForManagedSystems'))
            user.permission_all_access = self._parse_bool(user_raw.get('PermissionAllAccess'))
            user.permission_create_refresh_system_job = self._parse_bool(
                user_raw.get('PermissionCreateRefreshSystemJob'))
            user.permission_edit_delegation = self._parse_bool(user_raw.get('PermissionEditDelegation'))
            user.permission_edit_password_lists = self._parse_bool(user_raw.get('PermissionEditPasswordLists'))
            user.permission_edit_stored_passwords = self._parse_bool(user_raw.get('PermissionEditStoredPasswords'))
            user.permission_elevate_account_permissions = self._parse_bool(
                user_raw.get('PermissionElevateAccountPermissions'))
            user.permission_elevate_any_account_permissions = self._parse_bool(
                user_raw.get('PermissionElevateAnyAccountPermissions'))
            user.permission_grant_password_requests = self._parse_bool(user_raw.get('PermissionGrantPasswordRequests'))
            user.permission_ignore_password_checkout = self._parse_bool(
                user_raw.get('PermissionIgnorePasswordCheckout'))
            user.permission_logon = self._parse_bool(user_raw.get('PermissionLogon'))
            user.permission_personal_store = self._parse_bool(user_raw.get('PermissionPersonalStore'))
            user.permission_request_passwords = self._parse_bool(user_raw.get('PermissionRequestPasswords'))
            user.permission_request_remote_access = self._parse_bool(user_raw.get('PermissionRequestRemoteAccess'))
            user.permission_require_oath = self._parse_bool(user_raw.get('PermissionRequireOATH'))
            user.permission_require_rsa_secure_id = self._parse_bool(user_raw.get('PermissionRequireRSASecurID'))
            user.permission_self_recovery = self._parse_bool(user_raw.get('PermissionSelfRecovery'))
            user.permission_view_accounts = self._parse_bool(user_raw.get('PermissionViewAccounts'))
            user.permission_view_dashboards = self._parse_bool(user_raw.get('PermissionViewDashboards'))
            user.permission_view_delegation = self._parse_bool(user_raw.get('PermissionViewDelegation'))
            user.permission_view_file_store = self._parse_bool(user_raw.get('PermissionViewFileStore'))
            user.permission_view_jobs = self._parse_bool(user_raw.get('PermissionViewJobs'))
            user.permission_view_password_activity = self._parse_bool(user_raw.get('PermissionViewPasswordActivity'))
            user.permission_view_password_history = self._parse_bool(user_raw.get('PermissionViewPasswordHistory'))
            user.permission_view_passwords = self._parse_bool(user_raw.get('PermissionViewPasswords'))
            user.permission_view_scheduler = self._parse_bool(user_raw.get('PermissionViewScheduler'))
            user.permission_view_systems = self._parse_bool(user_raw.get('PermissionViewSystems'))
            user.permission_view_web_logs = self._parse_bool(user_raw.get('PermissionViewWebLogs'))

        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('AccountName')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = user_id

            user.username = user_id
            user.display_name = user_raw.get('DisplayName')
            user.mail = user_raw.get('EmailAddress')
            user.is_admin = self._parse_bool(user_raw.get('PermissionAllAccess'))
            user.is_locked = self._parse_bool(user_raw.get('PermissionLogon')) is False

            self._fill_beyond_trust_privileged_identity_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching BeyondTrustPrivilegedIdentity User for {user_raw}')
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
                logger.exception(f'Problem with fetching BeyondTrustPrivilegedIdentity User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
