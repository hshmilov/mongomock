import json
import logging

from axonius.clients.g_suite_admin_connection import GSuiteAdminConnection
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter

logger = logging.getLogger(f'axonius.{__name__}')

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.adapter_exceptions import ClientConnectionException
from dateutil.parser import parse as parse_date
from datetime import datetime

# Required scopes by the json key credentials for mobile devices
MOBILE_SCOPES = ['https://www.googleapis.com/auth/admin.directory.device.mobile.readonly']
# Required scopes by the json key credentials for users
USER_SCOPES = ['https://www.googleapis.com/auth/admin.directory.user.readonly']


class OauthApp(SmartJsonClass):
    anonymous = Field(bool, 'Anonymous')
    client_id = Field(str, 'Client ID')
    display_text = Field(str, 'Display Text')
    etag = Field(str, 'ETag')
    kind = Field(str, 'Kind')
    native_app = Field(bool, 'Native App')
    scopes = ListField(str, 'Scopes')


class GoogleMdmAdapter(AdapterBase):
    """
    Adapter to access Google MDM suite
    """

    class MyDeviceAdapter(DeviceAdapter):
        adb_status = Field(bool, "Is ADB enabled")
        emails = ListField(str, "Emails for this device")
        device_password_status = Field(str, 'Device Password Status')
        first_sync = Field(datetime, 'First Sync')
        developer_options_status = Field(bool, 'Developer Options Status')

    class MyUserAdapter(UserAdapter):
        alias_emails = ListField(str, 'Alias Emails')
        is_mfa_enrolled = Field(bool, 'Is MFA Enrolled')
        is_mfa_enforced = Field(bool, 'Is MFA Enforced')
        is_delegated_admin = Field(bool, 'Is Delegated Admin')
        recovery_phone = Field(str, 'Recovery Phone')
        oauth_apps = ListField(OauthApp, 'Oauth Apps')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        auth_file = json.loads(self._grab_file_contents(client_config['keypair_file']))
        return auth_file['client_id']

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config) -> GSuiteAdminConnection:
        try:
            auth_file = json.loads(self._grab_file_contents(client_config['keypair_file']))
            scopes = MOBILE_SCOPES + USER_SCOPES
            conn = GSuiteAdminConnection(
                auth_file, client_config['account_to_impersonate'], scopes,
                client_config.get('get_oauth_apps') or False,
            )
            next(conn.get_users())    # try to connect
            return conn
        except Exception as e:
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data: GSuiteAdminConnection):
        return client_data.get_mobile_devices()

    # pylint: disable=arguments-differ
    def _query_users_by_client(self, client_name, client_data: GSuiteAdminConnection):
        return client_data.get_users()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "account_to_impersonate",
                    "title": "Email of an admin account to impersonate",
                    "type": "string"
                },
                {
                    "name": "keypair_file",
                    "title": "JSON Key pair for the service account",
                    "description": "The binary contents of the keypair file",
                    "type": "file",
                },
                {
                    "name": "get_oauth_apps",
                    "title": "Get OAuth Apps",
                    "description": "Get OAuth Apps (requires additional scope)",
                    "type": "bool",
                },
            ],
            "required": [
                'account_to_impersonate', 'keypair_file', 'get_oauth_apps'
            ],
            "type": "array"
        }

    def create_device(self, raw_device_data):
        device = self._new_device_adapter()
        device.id = raw_device_data.get('deviceId')
        if not device.id:
            logger.warning(f"Device {str(raw_device_data)} has no id")
            return
        device.set_raw(raw_device_data)
        os = raw_device_data.get('os')
        device.figure_os(os)
        emails = raw_device_data.get('email')
        primary_email = None
        if isinstance(emails, list):
            device.emails = emails
            primary_email = emails[0]
        elif isinstance(emails, str):
            device.emails = emails
        model = raw_device_data.get('model')
        device_model = model
        device.device_model = device_model
        device_type = raw_device_data.get('type')
        device.device_model_family = device_type
        mac = raw_device_data.get('wifiMacAddress')
        if mac:
            device.add_nic(mac)
        name = f'{model} ' if model else ''
        if os:
            name += f'{os} '
        if primary_email:
            name += f'{primary_email} '
        device.name = name
        device.device_password_status = raw_device_data.get('devicePasswordStatus')
        first_sync = raw_device_data.get('firstSync')
        try:
            if first_sync:
                device.first_sync = parse_date(first_sync)
        except Exception:
            logger.exception(f'Can not parse First Sync {first_sync}')
        last_sync = raw_device_data.get('lastSync')
        try:
            if last_sync:
                device.last_seen = parse_date(last_sync)
        except Exception:
            logger.exception(f'Can not parse last sync {last_sync}')

        try:
            device.adb_status = raw_device_data.get('adbStatus')
        except Exception:
            logger.exception(f'Can not set adb status')

        try:
            device.developer_options_status = raw_device_data.get('developerOptionsStatus')
        except Exception:
            logger.exception(f'Can not set developer options status')

        device.adapter_properties = [AdapterProperty.Agent.name, AdapterProperty.MDM.name]
        return device

    def _parse_raw_data(self, raw_data):
        for raw_device_data in iter(raw_data):
            try:
                device = self.create_device(raw_device_data)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    def create_user(self, raw_user_data):
        user = self._new_user_adapter()
        user.id = raw_user_data.get('id')
        if not user.id:
            logger.warning(f"User {raw_user_data} has no id")
            return
        user.set_raw(raw_user_data)
        user.is_admin = raw_user_data.get('isAdmin', None)
        user.is_delegated_admin = raw_user_data.get('isDelegatedAdmin')
        user.is_mfa_enrolled = raw_user_data.get('isEnrolledIn2Sv')
        user.is_mfa_enforced = raw_user_data.get('isEnforcedIn2Sv')
        user.account_disabled = raw_user_data.get('suspended', None)
        user.user_created = parse_date(raw_user_data.get('creationTime'))
        if raw_user_data.get('orgUnitPath'):
            try:
                user.organizational_unit.append(raw_user_data.get('orgUnitPath'))
            except Exception:
                logger.exception(f'Failed adding organizational unit')
        try:
            user.last_logon = parse_date(raw_user_data['lastLoginTime'])
        except Exception:
            # invalid date or something
            logger.exception(f"Couldn't get lst login time for {raw_user_data}")
        raw_name = raw_user_data.get('name')
        if raw_name:
            user.first_name = raw_name.get('givenName')
            user.last_name = raw_name.get('familyName')
            user.username = raw_name.get('fullName')
        user.mail = raw_user_data.get('primaryEmail')
        try:
            if raw_user_data.get('aliases') and isinstance(raw_user_data.get('aliases'), list):
                user.alias_emails = raw_user_data.get('aliases')
        except Exception:
            logger.exception(f'Problem getting aliasse for user {raw_user_data}')

        try:
            phones = [p.get('value') for p in (raw_user_data.get('phones') or [])]
            user.user_telephone_number = ','.join(phones)
        except Exception:
            logger.exception(f'Failed setting phones')

        user.recovery_phone = raw_user_data.get('recoveryPhone')

        try:
            for token_raw in ((raw_user_data.get('tokens') or {}).get('items') or []):
                try:
                    native_app = token_raw.get('nativeApp')
                    anonymous = token_raw.get('anonymous')
                    scopes = [str(scope_i) for scope_i in token_raw.get('scopes')]
                    user.oauth_apps.append(
                        OauthApp(
                            anonymous=anonymous if isinstance(anonymous, bool) else None,
                            client_id=token_raw.get('clientId'),
                            display_text=token_raw.get('displayText'),
                            etag=token_raw.get('etag'),
                            kind=token_raw.get('kind'),
                            native_app=native_app if isinstance(native_app, bool) else None,
                            scopes=scopes,
                        )
                    )
                except Exception:
                    logger.exception(f'Failed adding oauth app')
        except Exception:
            logger.exception(f'Failed settings oauth app')

        # getting user photo might be tricky, and might require more permissions
        # https://stackoverflow.com/questions/25467326/retrieving-google-user-photo
        return user

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, raw_data):
        for raw_user_data in iter(raw_data):
            try:
                user = self.create_user(raw_user_data)
                if user:
                    yield user
            except Exception:
                logger.exception(f'Got exception for raw_user_data: {raw_user_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
