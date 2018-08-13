import logging

from axonius.utils.parsing import parse_date

from axonius.adapter_exceptions import ClientConnectionException
from axonius.users.user_adapter import UserAdapter
from okta_adapter.connection import OktaConnection

logger = logging.getLogger(f'axonius.{__name__}')

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
import hashlib


class OktaAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    class MyUserAdapter(UserAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        api_declassified = hashlib.md5(client_config['api_key'].encode('utf-8')).hexdigest()
        return f"{client_config['url']}_{api_declassified}"

    def _connect_client(self, client_config):
        connection = OktaConnection(**client_config)
        try:
            connection.is_alive()
        except Exception as e:
            raise ClientConnectionException(e)
        return connection

    def _query_users_by_client(self, client_name, client_data):
        return client_data.get_users()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "url",
                    "title": "Okta URL",
                    "type": "string"
                },
                {
                    "name": "api_key",
                    "title": "Okta API key",
                    "type": "string",
                    "format": "password"
                },
            ],
            "required": [
                "url",
                "api_key",
            ],
            "type": "array"
        }

    def _parse_users_raw_data(self, raw_data):
        for user_raw in raw_data:
            try:
                # Schema defined here https://developer.okta.com/docs/api/resources/users#user-model
                user = self._new_user_adapter()
                profile = user_raw['profile']
                user.id = user_raw['id']
                user.account_disabled = user_raw.get('status') in ('PROVISIONED', 'ACTIVE')
                user.last_seen = parse_date(user_raw.get('last_login'))
                user.last_password_change = parse_date(user_raw.get('passwordChanged'))
                user.user_created = parse_date(user_raw.get('created'))
                user.mail = profile.get('email')
                user.username = profile.get('login') or user.mail
                if not user.username:
                    # according to `user_adapter.py` - a username is required for every User adapter
                    logger.error("User without email and login from Okta")
                    continue
                user.first_name = profile.get('firstName')
                user.last_name = profile.get('lastName')
                user.user_telephone_number = profile.get('mobilePhone')
                user.user_title = profile.get('title')
                user.user_department = profile.get('department')
                user.user_country = profile.get('countryCode')
                user.set_raw(user_raw)
                yield user
            except Exception:
                logger.exception(f"Problem parsing user: {str(user_raw)}")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
