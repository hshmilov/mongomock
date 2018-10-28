
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from nimbul_adapter.connection import NimbulConnection

logger = logging.getLogger(f'axonius.{__name__}')


class NimbulAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        public_ip = ListField(str, 'Public IPs')
        app_code = Field(str, 'Application Code')
        app_description = Field(str, 'Application Description')
        app_email = Field(str, 'Application Email')
        cluster_name = Field(str, 'Cluster Name')
        environment_name = Field(str, 'Environment Name')
        subnet_name = Field(str, 'Subnet Name')

    class MyUserAdapter(UserAdapter):
        nimbul_source = Field(str, 'Nimbul Source')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['token']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability('https://nimbul-api.nyt.net')

    def _connect_client(self, client_config):
        try:
            connection = NimbulConnection(domain='https://nimbul-api.nyt.net',
                                          url_base_prefix='api/v1/',
                                          apikey=client_config['token'])
            with connection:
                pass
            return connection
        except Exception as e:
            # pylint: disable=W1202
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        with client_data:
            yield from client_data.get_device_list()

    def _query_users_by_client(self, key, data):
        with data:
            yield from data.get_user_list()

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'token',
                    'title': 'API Token',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'token'
            ],
            'type': 'array'
        }

    def _create_device_instance(self, device_raw):
        device = self._new_device_adapter()
        if not device_raw.get('instance_id'):
            logger.warning(f'Bad device with no ID {device_raw}')
            return None
        device.id = str(device_raw.get('instance_id'))
        device.hostname = device_raw.get('hostname')
        device.app_code = device_raw.get('app_code')
        device.app_description = device_raw.get('app_description')
        device.app_email = device_raw.get('app_email')
        device.cluster_name = device_raw.get('cluster_name')
        device.environment_name = device_raw.get('environment_name')
        device.subnet_name = device_raw.get('subnet_name')

        try:
            subnet = device_raw.get('subnet')
            if subnet and isinstance(subnet, str):
                subnets = [subnet]
            else:
                subnets = None
            private_ip = device_raw.get('private_ip')
            if private_ip and isinstance(private_ip, str):
                private_ip = [private_ip]
            if private_ip:
                device.add_nic(None, private_ip, subnets=subnets)

            public_ip = device_raw.get('public_ip')
            if public_ip and isinstance(public_ip, str):
                public_ip = [public_ip]
            if public_ip:
                device.add_nic(None, public_ip)
                device.public_ip = public_ip
        except Exception:
            logger.exception(f'Problem getting ip for {device_raw}')

        device.set_raw(device_raw)
        return device

    def _create_device_unmanaged(self, device_raw):
        device = self._new_device_adapter()
        if not device_raw.get('id'):
            logger.warning(f'Bad device with no ID {device_raw}')
            return None
        device.id = str(device_raw.get('id')) + str(device_raw.get('cloud_uid'))
        device.name = device_raw.get('cloud_uid')
        try:
            private_ip = device_raw.get('private_ip_address')
            if private_ip and isinstance(private_ip, str):
                private_ip = [private_ip]
            if private_ip:
                device.add_nic(None, private_ip)

            public_ip = device_raw.get('public_ip_address')
            if public_ip and isinstance(public_ip, str):
                public_ip = [public_ip]
            if public_ip:
                device.add_nic(None, public_ip)
                device.public_ip = public_ip
        except Exception:
            logger.exception(f'Problem getting ip for {device_raw}')
        device.set_raw(device_raw)
        return device

    def _create_user_user(self, user_raw):
        user = self._new_user_adapter()
        mail = user_raw.get('email')
        if not mail:
            return None
        user.id = mail
        user.mail = mail
        user.nimbul_source = user_raw.get('source')
        user.set_raw(user_raw)
        return user

    # pylint: disable=W0221
    def _parse_users_raw_data(self, raw_users):
        for user_type, user_raw in iter(raw_users):
            try:
                user = None
                if user_type == 'user':
                    user = self._create_user_user(user_raw)
                if user:
                    yield user
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {user_raw}')

    def _parse_raw_data(self, devices_raw_data):
        for device_type, device_raw in iter(devices_raw_data):
            try:
                device = None
                if device_type == 'unmanaged':
                    device = self._create_device_unmanaged(device_raw)
                elif device_type == 'instance':
                    device = self._create_device_instance(device_raw)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
