import json
import logging
import os

from axonius.clients.g_suite_admin_connection import GSuiteAdminConnection
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.clients.rest.connection import RESTConnection
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
MOBILE_DEVICE = 'Mobile Device'
CHROMEOS_DEVICE = 'ChromeOS Device'


class OauthApp(SmartJsonClass):
    anonymous = Field(bool, 'Anonymous')
    client_id = Field(str, 'Client ID')
    display_text = Field(str, 'Display Text')
    etag = Field(str, 'ETag')
    kind = Field(str, 'Kind')
    native_app = Field(bool, 'Native App')
    scopes = ListField(str, 'Scopes')
    scopes_descriptions = ListField(str, 'Scopes Descriptions')


class GoogleMdmAdapter(AdapterBase):
    """
    Adapter to access Google MDM suite
    """

    class MyDeviceAdapter(DeviceAdapter):
        chrome_device_type = Field(str, 'Chrome Device Type', enum=[CHROMEOS_DEVICE, MOBILE_DEVICE])
        adb_status = Field(bool, "Is ADB enabled")
        emails = ListField(str, "Emails for this device")
        device_password_status = Field(str, 'Device Password Status')
        first_sync = Field(datetime, 'First Sync')
        developer_options_status = Field(bool, 'Developer Options Status')
        managed_account_is_on_owner_profile = Field(bool, 'Managed Account Is On Owner Profile')
        encryption_status = Field(str, 'Encryption Status')
        security_patch_level_str = Field(str, 'Security Patch Level String')
        privilege = Field(str, 'Privilege')
        device_status = Field(str, 'Device Status')
        notes = Field(str, 'Notes')
        org_unit_path = Field(str, 'Org Unit Path')
        meid = Field(str, 'MEID')
        order_number = Field(str, 'Order Number')

    class MyUserAdapter(UserAdapter):
        alias_emails = ListField(str, 'Alias Emails')
        is_mfa_enrolled = Field(bool, 'Is MFA Enrolled')
        is_mfa_enforced = Field(bool, 'Is MFA Enforced')
        suspended = Field(bool, 'Suspended')
        is_delegated_admin = Field(bool, 'Is Delegated Admin')
        recovery_phone = Field(str, 'Recovery Phone')
        oauth_apps = ListField(OauthApp, 'Oauth Apps')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        try:
            with open(os.path.join(os.path.dirname(__file__), 'oauth2_scopes.json'), 'rt') as f:
                self.oauth2_scopes = json.loads(f.read())
        except Exception:
            logger.exception(f'Problem reading oauth2_scopes')
            self.oauth2_scopes = dict()

    def _get_client_id(self, client_config):
        auth_file = json.loads(self._grab_file_contents(client_config['keypair_file']))
        return auth_file['client_id']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('https://developers.google.com/'))

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
        return client_data.get_mobile_devices(), client_data.get_chromeosdevices_devices()

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

    def create_chromeosdevices_device(self, raw_device_data):
        device = self._new_device_adapter()
        device.chrome_device_type = CHROMEOS_DEVICE
        device.id = raw_device_data.get('deviceId')
        if not device.id:
            logger.warning(f"Device {str(raw_device_data)} has no id")
            return
        device.set_raw(raw_device_data)
        device.order_number = raw_device_data.get('orderNumber')
        os = raw_device_data.get('osVersion')
        device.figure_os(os)
        device.device_model = raw_device_data.get('model')
        device.meid = raw_device_data.get('meid')
        if raw_device_data.get('macAddress'):
            device.add_nic(mac=raw_device_data.get('macAddress'))
        if raw_device_data.get('ethernetMacAddress'):
            device.add_nic(mac=raw_device_data.get('ethernetMacAddress'))
        device.device_serial = raw_device_data.get('serialNumber')
        device.device_status = raw_device_data.get('status')
        device.last_seen = parse_date(raw_device_data.get('lastSync'))
        device.notes = raw_device_data.get('notes')
        users_raw = raw_device_data.get('recentUsers')
        if not isinstance(users_raw, list):
            users_raw = []
        for user_raw in users_raw:
            if not isinstance(user_raw, dict):
                continue
            if user_raw.get('email'):
                device.last_used_users.append(user_raw.get('email'))
        device.org_unit_path = raw_device_data.get('orgUnitPath')
        device.adapter_properties = [AdapterProperty.Agent.name, AdapterProperty.MDM.name]
        return device

    def create_mobile_device(self, raw_device_data):
        device = self._new_device_adapter()
        device.chrome_device_type = MOBILE_DEVICE
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
        if isinstance(raw_device_data.get('managedAccountIsOnOwnerProfile'), bool):
            device.managed_account_is_on_owner_profile = raw_device_data.get('managedAccountIsOnOwnerProfile')
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
        device.device_serial = raw_device_data.get('serialNumber')
        device.device_password_status = raw_device_data.get('devicePasswordStatus')
        device.encryption_status = raw_device_data.get('encryptionStatus')
        device.security_patch_level_str = raw_device_data.get('securityPatchLevel')
        device.privilege = raw_device_data.get('privilege')
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
        raw_data_mobile, raw_data_chromeosdevices = raw_data
        for raw_device_data in iter(raw_data_mobile):
            try:
                device = self.create_mobile_device(raw_device_data)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

        for raw_device_data in iter(raw_data_chromeosdevices):
            try:
                device = self.create_chromeosdevices_device(raw_device_data)
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
        try:
            user.account_disabled = raw_user_data.get('suspended', None)
            user.suspended = raw_user_data.get('suspended', None)
        except Exception:
            logger.exception(f'Could not set suspended data')
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
                    scopes_descriptions = [
                        self.oauth2_scopes.get(scope) for scope in scopes if self.oauth2_scopes.get(scope)
                    ]
                    user.oauth_apps.append(
                        OauthApp(
                            anonymous=anonymous if isinstance(anonymous, bool) else None,
                            client_id=token_raw.get('clientId'),
                            display_text=token_raw.get('displayText'),
                            etag=token_raw.get('etag'),
                            kind=token_raw.get('kind'),
                            native_app=native_app if isinstance(native_app, bool) else None,
                            scopes=scopes,
                            scopes_descriptions=scopes_descriptions
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
