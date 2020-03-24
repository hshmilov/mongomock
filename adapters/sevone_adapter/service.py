import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from sevone_adapter.connection import SevoneConnection
from sevone_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class SevoneAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        is_new = Field(bool, 'Is New')
        is_deleted = Field(bool, 'Is Deleted')
        alternate_name = Field(str, 'Alternate Name')
        manual_ip = Field(bool, 'Manual IP')

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
    def get_connection(client_config):
        connection = SevoneConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      https_proxy=client_config.get('https_proxy'),
                                      username=client_config['username'],
                                      password=client_config['password'])
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
    def _clients_schema():
        """
        The schema SevoneAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Sevone Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
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
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _create_device(device_raw, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')
            device.hostname = device_raw.get('name')
            if isinstance(device_raw.get('ipAddress'), str):
                device.add_nic(ips=device_raw.get('ipAddress').split(','))
            device.last_seen = parse_date(device_raw.get('lastDiscovery'))
            device.description = device_raw.get('description')
            device.time_zone = device_raw.get('timezone')

            try:
                if isinstance(device_raw.get('isNew'), bool):
                    device.is_new = device_raw.get('isNew')
                if isinstance(device_raw.get('isDeleted'), bool):
                    device.is_deleted = device_raw.get('isDeleted')
                if isinstance(device_raw.get('manualIP'), bool):
                    device.manual_ip = device_raw.get('manualIP')
            except Exception:
                logger.exception(f'Could not set bool fields')
            device.alternate_name = device_raw.get('alternateName')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Sevone Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw, self._new_device_adapter())
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
