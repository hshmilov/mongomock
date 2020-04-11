import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from zoom_adapter.connection import ZoomConnection
from zoom_adapter.client_id import get_client_id
from zoom_adapter.consts import ZOOM_USER_TYPE, ZOOM_VERIFIED, ZOOM_DEFAULT_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class ZoomAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(UserAdapter):
        user_type = Field(str, 'User Type')
        timezone = Field(str, 'Timezone')
        last_client_version = Field(str, 'Last Client Version')
        pmi = Field(int, 'PMI')
        verified = Field(bool, 'Verified')
        im_groups = ListField(str, 'IM Groups')

    class MyDeviceAdapter(DeviceAdapter):
        protocol = Field(str, 'Protocol')
        encryption = Field(str, 'Encryption')

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
    def get_connection(client_config):
        connection = ZoomConnection(domain=client_config['domain'],
                                    apikey=client_config['apikey'],
                                    verify_ssl=client_config['verify_ssl'],
                                    api_secret=client_config['api_secret'],
                                    https_proxy=client_config.get('https_proxy')
                                    )
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint: disable=arguments-differ
    @staticmethod
    def _query_users_by_client(key, data):
        with data:
            yield from data.get_user_list()

    def _create_user(self, user_raw, groups_dict, im_groups_dict):
        try:
            user = self._new_user_adapter()
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('email') or '')
            user.first_name = user_raw.get('first_name')
            user.last_name = user_raw.get('last_name')
            user.username = (user_raw.get('first_name') or '') + ' ' + (user_raw.get('last_name') or '')
            user.mail = user_raw.get('email')
            user.user_created = parse_date(user_raw.get('created_at'))
            user.last_logon = parse_date(user_raw.get('last_login_time'))
            user.user_status = user_raw.get('status')
            user.user_department = user_raw.get('dept')
            user.pmi = user_raw.get('pmi') if isinstance(user_raw.get('pmi'), int) else None
            user.user_type = ZOOM_USER_TYPE.get(user_raw.get('type'))
            user.verified = ZOOM_VERIFIED.get(user_raw.get('verified'))
            user.timezone = user_raw.get('timezone')
            group_ids = user_raw.get('group_ids')
            if not isinstance(group_ids, list):
                group_ids = []
            for group_id in group_ids:
                if groups_dict.get(group_id):
                    user.groups.append(groups_dict.get(group_id).get('name'))
            im_group_ids = user_raw.get('im_group_ids')
            if not isinstance(im_group_ids, list):
                im_group_ids = []
            for im_group_id in im_group_ids:
                if im_groups_dict.get(im_group_id):
                    user.im_groups.append(im_groups_dict.get(im_group_id).get('name'))
            user.last_client_version = user_raw.get('last_client_version')
            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching Zoom user for {user_raw}')
            return None

    def _parse_users_raw_data(self, users_raw_data):
        for user_raw, groups_dict, im_groups_dict in users_raw_data:
            user = self._create_user(user_raw, groups_dict, im_groups_dict)
            if user:
                yield user

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.hostname = device_raw.get('name')
            device.add_nic(ips=[device_raw.get('ip')])
            device.protocol = device_raw.get('protocol')
            device.encryption = device_raw.get('encryption')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Zoom Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @staticmethod
    def _clients_schema():
        """
        The schema ZoomAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Zoom Domain',
                    'type': 'string',
                    'default': ZOOM_DEFAULT_DOMAIN
                },
                {
                    'name': 'apikey',
                    'type': 'string',
                    'title': 'JWT API Key'
                },
                {
                    'name': 'api_secret',
                    'type': 'string',
                    'format': 'password',
                    'title': 'JWT API Secret'
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
                'verify_ssl',
                'api_secret',
                'apikey'
            ],
            'type': 'array'
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement, AdapterProperty.Agent]
