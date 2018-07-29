import logging
from datetime import datetime
import duo_client

from axonius.users.user_adapter import UserAdapter

logger = logging.getLogger(f"axonius.{__name__}")

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.utils.files import get_local_config_file
from axonius.adapter_exceptions import ClientConnectionException


class DuoAdapter(AdapterBase):
    class MyUserAdapter(UserAdapter):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['host']

    def _connect_client(self, client_config):
        try:
            admin_api = duo_client.Admin(
                ikey=client_config['instance_key'],
                skey=client_config['secret_key'],
                host=client_config['host'],
            )
            admin_api.get_users()  # make sure client is valid
            return admin_api
        except Exception as e:
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_users_by_client(self, client_name, session):
        return session.get_users()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "host",
                    "title": "Host",
                    "type": "string",
                },
                {
                    "name": "instance_key",
                    "title": "Instance key",
                    "type": "string"
                },
                {
                    "name": "secret_key",
                    "title": "Secret key",
                    "type": "string",
                    "format": "password"
                },
            ],
            "required": [
                "host",
                "instance_key",
                "secret_key"
            ],
            "type": "array"
        }

    def _create_user(self, raw_user_data):
        user = self._new_user_adapter()
        user.id = raw_user_data['user_id']
        user.set_raw(raw_user_data)
        user.mail = raw_user_data.get('email')
        user.username = raw_user_data.get('username')
        user.first_name = raw_user_data.get('firstname') or raw_user_data.get('realname')
        user.last_name = raw_user_data.get('lastname')
        last_logon_raw = raw_user_data.get('last_login')
        if last_logon_raw:
            try:
                user.last_logon = datetime.fromtimestamp(last_logon_raw)
            except Exception:
                logger.exception(f"Couldn't get last logon for {raw_user_data}")
        return user

    def _parse_users_raw_data(self, raw_data):
        for raw_user_data in iter(raw_data):
            try:
                device = self._create_user(raw_user_data)
                yield device
            except Exception:
                logger.exception(f'Got exception for raw_user_data: {raw_user_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
