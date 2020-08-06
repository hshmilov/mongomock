import datetime
import logging

# pylint: disable=import-error
from boxsdk import Client, JWTAuth
from boxsdk.config import Proxy

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.json import from_json
from box_platform_adapter.client_id import get_client_id
from box_platform_adapter.consts import DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class NotificationEmail(SmartJsonClass):
    email = Field(str, 'Email')
    is_confirmed = Field(bool, 'Email Confirmed')


class BoxPlatformAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(UserAdapter):
        modified = Field(datetime.datetime, 'User Last Modified')
        language = Field(str, 'Language')
        timezone = Field(str, 'Timezone')
        space_amount = Field(int, 'Available Space (Bytes)')
        space_used = Field(int, 'Space Used (Bytes)')
        max_upload_size = Field(int, 'Max Upload Size')
        address = Field(str, 'Address')
        role = Field(str, 'Role')
        can_see_managed_users = Field(bool, 'Can See Managed Users')
        is_sync_enabled = Field(bool, 'Sync Enabled')
        is_external_collab_restricted = Field(bool, 'External Collab Restricted')
        is_exempt_from_device_limits = Field(bool, 'Exempt From Device Limits')
        is_exempt_from_login_verify = Field(bool, 'Exempt From Login Verification')
        hostname = Field(str, 'Hostname')
        is_platform_access_only = Field(bool, 'Platform Access Only')
        external_app_user_id = Field(str, 'External App User ID')
        # email_confirmed = Field(bool, 'Email Confirmed')
        notif_emails = ListField(NotificationEmail, 'Notification Email')
        user_tags = ListField(str, 'Custom User Tags')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability('https://api.box.com/2.0',
                                                https_proxy=client_config.get('https_proxy'))

    def _get_box_config(self, client_config):
        proxy_url = client_config.get('https_proxy')
        if proxy_url:
            Proxy.URL = proxy_url
        config_file = self._grab_file_contents(client_config['config_json'])
        settings_json = from_json(config_file)
        return JWTAuth.from_settings_dictionary(settings_json)

    def _connect_client(self, client_config):
        try:
            config = self._get_box_config(client_config)
            client = Client(config)
            next(client.users(limit=1), None)
            return client
        except Exception as e:
            message = 'Error connecting to client with enterprise ID {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint:disable=arguments-differ
    @staticmethod
    def _query_users_by_client(client_name, client_data):
        """
        Yield all users from a specific  domain.
        Call result.response_object to get the raw JSON representing the result object. Example:
        for result in boxadapter._query_users_by_client(...):
            print(result.response_object)

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: Iterable(boxsdk.user.User) with all the attributes returned from the Server.
        """
        yield from client_data.users(user_type='all', limit=DEVICE_PER_PAGE)  # This Client automatically does paging

    @staticmethod
    def _clients_schema():
        """
        The schema BoxPlatformAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Box Platform enterprise ID',
                    'type': 'string'
                },
                {
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
                },
                {
                    'name': 'config_json',
                    'title': 'Box Platform private key configuration file',
                    'type': 'file'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'client_id',
                'config_json',
            ],
            'type': 'array'
        }

    @staticmethod
    def _parse_int(value):
        try:
            return int(value)
        except Exception:
            return None

    @staticmethod
    def _parse_bool(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() == 'true'
        if isinstance(value, int):
            return bool(value)
        return None

    # pylint:disable=too-many-statements
    def _create_user(self, user_raw_obj):
        # User object reference: https://developer.box.com/reference/resources/user/
        try:
            user_raw = user_raw_obj.response_object
            user = self._new_user_adapter()
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            # Axonius generic stuff
            user.id = user_id + '_' + (user_raw.get('login') or '')
            user.display_name = user_raw.get('name')
            user.mail = user_raw.get('login')  # This is "The primary email address of this user" (from docs)
            user.user_telephone_number = user_raw.get('phone')
            user.user_title = user_raw.get('job_title')
            user.image = user_raw.get('avatar_url')
            try:
                user.user_created = parse_date(user_raw.get('created_at'))
            except Exception:
                logger.warning(f'Failed to parse creation date for {user_raw}')
            user.user_status = user_raw.get('status')
            user.username = user_raw.get('login')
            user.is_admin = user_raw.get('role', '') in ['admin', 'coadmin']
            # Box platform specific stuff
            try:
                user.modified = parse_date(user_raw.get('modified_at'))
            except Exception:
                logger.warning(f'Failed to parse modified date for {user_raw}')
            user.language = user_raw.get('language')
            user.timezone = user_raw.get('timezone')
            user.space_amount = self._parse_int(user_raw.get('space_amount'))
            user.space_used = self._parse_int(user_raw.get('space_used'))
            user.max_upload_size = self._parse_int(user_raw.get('max_upload_suze'))
            user.address = user_raw.get('address')
            user.role = user_raw.get('role')
            user.can_see_managed_users = self._parse_bool(user_raw.get('can_see_managed_users'))
            user.is_sync_enabled = self._parse_bool(user_raw.get('is_sync_enabled'))
            user.is_external_collab_restricted = self._parse_bool(user_raw.get('is_external_collab_restricted'))
            user.is_exempt_from_device_limits = self._parse_bool(user_raw.get('is_exempt_from_device_limits'))
            user.is_exempt_from_login_verify = self._parse_bool(user_raw.get('is_exempt_from_login_verification'))
            user.hostname = user_raw.get('hostname')
            user.is_platform_access_only = self._parse_bool(user_raw.get('is_platform_access_only'))
            user.external_app_user_id = user_raw.get('external_app_user_id')
            notif_emails_raw = user_raw.get('notification_email')
            if isinstance(notif_emails_raw, dict):
                notif_emails_raw = [notif_emails_raw]
            if isinstance(notif_emails_raw, list):
                user_notif_emails = list()
                for notif_email_data in notif_emails_raw:
                    if not isinstance(notif_email_data, dict):
                        logger.warning(f'Failed to parse email data for {user_raw_obj} from {notif_email_data}')
                        continue
                    email_confirmed = self._parse_bool(notif_email_data.get('is_confirmed'))
                    notif_email = notif_email_data.get('email')
                    user_notif_emails.append(NotificationEmail(
                        email=notif_email,
                        is_confirmed=email_confirmed
                    ))
                user.notif_emails = user_notif_emails
            user_tags = user_raw.get('my_tags') or None
            if isinstance(user_tags, list):
                user.user_tags = user_tags
            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching Box Platform user for {user_raw_obj}')
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
