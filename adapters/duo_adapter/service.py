import logging
from datetime import datetime
import duo_client

from axonius.users.user_adapter import UserAdapter
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.utils.files import get_local_config_file
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.datetime import parse_date
from axonius.smart_json_class import SmartJsonClass
from axonius.fields import Field, ListField
from axonius.clients.rest.connection import RESTConnection


logger = logging.getLogger(f'axonius.{__name__}')


USERS_PER_PAGE = 100
MAX_USERS = 1000000


class DuoGroup(SmartJsonClass):
    description = Field(str, 'Description')
    name = Field(str, 'Name')
    status = Field(str, 'Status')
    push_enabled = Field(bool, 'Push Enabled')
    sms_enabled = Field(bool, 'SMS Enabled')
    mobile_otp_enabled = Field(bool, 'Mobile OTP Enabled')
    voice_enabled = Field(bool, 'Voice Enabled')


class DuoAdapter(AdapterBase):
    class MyUserAdapter(UserAdapter):
        notes = Field(str, 'Notes')
        is_enrolled = Field(bool, 'Is Enrolled')
        duo_groups = ListField(DuoGroup, 'Duo Groups')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['host']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('host'))

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
        offset = 0
        yield from session.get_users(limit=USERS_PER_PAGE, offset=offset)
        offset += USERS_PER_PAGE
        while offset < MAX_USERS:
            try:
                response = session.get_users(limit=USERS_PER_PAGE, offset=offset)
                if not response:
                    break
                yield from response
                offset += USERS_PER_PAGE
            except Exception:
                logger.exception(f'Problem with offset {offset}')
                break

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "host",
                    "title": "Duo Admin API Host",
                    "type": "string",
                },
                {
                    "name": "instance_key",
                    "title": "Integration key",
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
        user.user_created = parse_date(raw_user_data.get('parse_date'))
        groups_raw = raw_user_data.get('groups')
        if not isinstance(groups_raw, list):
            groups_raw = []
        for group_raw in groups_raw:
            try:
                user.duo_groups.append(DuoGroup(name=group_raw.get('name'),
                                                description=group_raw.get('desc'),
                                                status=group_raw.get('status'),
                                                voice_enabled=group_raw.get('voice_enabled'),
                                                sms_enabled=group_raw.get('sms_enabled'),
                                                push_enabled=group_raw.get('push_enabled'),
                                                mobile_otp_enabled=group_raw.get('mobile_otp_enabled')))
            except Exception:
                logger.exception(f'Problem with group {group_raw}')

        if last_logon_raw:
            try:
                user.last_logon = datetime.fromtimestamp(last_logon_raw)
            except Exception:
                logger.exception(f"Couldn't get last logon for {raw_user_data}")
        user.is_enrolled = raw_user_data.get('is_enrolled') \
            if isinstance(raw_user_data.get('is_enrolled'), bool) else None
        user.notes = raw_user_data.get('notes')
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
