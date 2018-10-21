
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from nimbul_adapter.connection import NimbulConnection

logger = logging.getLogger(f'axonius.{__name__}')


class NimbulAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

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
        return device

    def _create_device_unmanaged(self, device_raw):
        device = self._new_device_adapter()
        return device

    def _create_user_app(self, user_raw):
        user = self._new_user_adapter()
        return user

    def _create_user_user(self, user_raw):
        user = self._new_user_adapter()
        return user

    # pylint: disable=W0221
    def _parse_users_raw_data(self, raw_users):
        for user_raw, user_type in iter(raw_users):
            try:
                user = None
                if user_type == 'user':
                    user = self._create_user_user(user_raw)
                elif user_type == 'app':
                    user = self._create_user_app(user_raw)
                if user:
                    yield user
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {user_raw}')

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in iter(devices_raw_data):
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
