import json
import logging

import requests

from axonius.clients.g_suite_admin_connection import GSuiteAdminConnection
from axonius.fields import Field, ListField
from axonius.users.user_adapter import UserAdapter

logger = logging.getLogger(f"axonius.{__name__}")

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.adapter_exceptions import ClientConnectionException
from dateutil.parser import parse as parse_date

# Required scopes by the json key credentials for mobile devices
MOBILE_SCOPES = ['https://www.googleapis.com/auth/admin.directory.device.mobile.readonly']
# Required scopes by the json key credentials for users
USER_SCOPES = ['https://www.googleapis.com/auth/admin.directory.user.readonly']


class GoogleMdmAdapter(AdapterBase):
    """
    Adapter to access Google MDM suite
    """

    class MyDeviceAdapter(DeviceAdapter):
        adbStatus = Field(bool, "Is ADB enabled")
        emails = ListField(str, "Emails for this device")

    class MyUserAdapter(UserAdapter):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        auth_file = json.loads(self._grab_file_contents(client_config['keypair_file']))
        return auth_file['client_id']

    def _connect_client(self, client_config) -> GSuiteAdminConnection:
        try:
            auth_file = json.loads(self._grab_file_contents(client_config['keypair_file']))
            return GSuiteAdminConnection(auth_file, client_config['account_to_impersonate'], MOBILE_SCOPES + USER_SCOPES)
        except Exception as e:
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data: GSuiteAdminConnection):
        return client_data.get_mobile_devices()

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
            ],
            "required": [
                'account_to_impersonate', 'keypair_file'
            ],
            "type": "array"
        }

    def create_device(self, raw_device_data):
        device = self._new_device_adapter()
        device.id = raw_device_data.get('deviceId')
        if not device.id:
            logger.warning(f"Device {raw_data} has no id")
            return
        device.set_raw(raw_device_data)
        device.figure_os(raw_device_data.get('os'))
        device.emails = raw_device_data.get('email')
        device.device_model = raw_device_data.get('model')
        device.device_model_family = raw_device_data.get('type')
        mac = raw_device_data.get('wifiMacAddress')
        if mac:
            device.add_nic(mac)
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
        try:
            user.last_logon = parse_date(raw_user_data['lastLoginTime'])
        except Exception:
            # invalid date or something
            pass
        raw_name = raw_user_data.get('name')
        if raw_name:
            user.first_name = raw_name.get('givenName')
            user.last_name = raw_name.get('familyName')
            user.username = raw_name.get('fullName')
        user.mail = raw_user_data.get('primaryEmail')

        # getting user photo might be tricky, and might require more permissions
        # https://stackoverflow.com/questions/25467326/retrieving-google-user-photo
        return user

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
        return [AdapterProperty.Agent]
