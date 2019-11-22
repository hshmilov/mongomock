import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.fields import Field
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from cherwell_adapter.connection import CherwellConnection
from cherwell_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class CherwellAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        bus_ob_rec_id = Field(str, 'BusObRecId')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = CherwellConnection(domain=client_config['domain'],
                                        verify_ssl=client_config['verify_ssl'],
                                        https_proxy=client_config.get('https_proxy'),
                                        username=client_config['username'],
                                        password=client_config['password'],
                                        client_id=client_config['client_id'])
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
        The schema CherwellAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Cherwell Domain',
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
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
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
                'client_id',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches
    def _create_device(self, device_raw, bus_ob_id, bus_ob_rec_id):
        try:
            device = self._new_device_adapter()
            device.id = bus_ob_id
            device.bus_ob_rec_id = bus_ob_rec_id
            for field_raw in device_raw:
                try:
                    mac = None
                    ips = None
                    field_name = field_raw.get('name')
                    field_value = field_raw.get('value')
                    if not field_name or not field_value:
                        continue
                    if field_name == 'SerialNumber':
                        device.device_serial = field_value
                    elif field_name == 'Model':
                        device.device_model = field_value
                    elif field_name == 'BIOSVersion':
                        device.bios_version = field_value
                    elif field_name == 'UserName':
                        device.last_used_users = [field_value]
                    elif field_name == 'OperatingSystem':
                        device.figure_os(field_value)
                    elif field_name == 'MACAddress':
                        mac = field_value
                    elif field_name == 'IPAddress':
                        ips = [field_value]
                    elif field_name == 'NumberCPUs':
                        # pylint: disable=invalid-name
                        device.total_number_of_physical_processors = field_value
                    if ips or mac:
                        device.add_nic(ips=ips, mac=mac)
                except Exception:
                    logger.exception(f'Problem with field {field_raw}')
            device.set_raw({'data': device_raw})
            return device
        except Exception:
            logger.exception(f'Problem with fetching Cherwell Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, bus_ob_id, bus_ob_rec_id in devices_raw_data:
            device = self._create_device(device_raw, bus_ob_id, bus_ob_rec_id)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
