import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from pure_storage_flash_array_adapter.connection import PureStorageFlashArrayConnection
from pure_storage_flash_array_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class PureStorageFlashArrayAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    def get_connection(self, client_config):
        connection = PureStorageFlashArrayConnection(domain=client_config['domain'],
                                                     verify_ssl=client_config['verify_ssl'],
                                                     https_proxy=client_config.get('https_proxy'),
                                                     application_id=client_config['application_id'],
                                                     private_key=self._grab_file_contents(
                                                         client_config['private_key_file']).decode('utf-8'))
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
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
        The schema PureStorageFlashArrayAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Pure Storage Pure1 Domain',
                    'type': 'string'
                },
                {
                    'name': 'application_id',
                    'title': 'Application ID',
                    'type': 'string'
                },
                {
                    'name': 'private_key_file',
                    'title': 'Private Key File',
                    'description': 'Unencrypted Private Key',
                    'type': 'file'
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
                'application_id',
                'private_key_file',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _create_device(device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            device.name = device_raw.get('name')
            device.figure_os(os_string=device_raw.get('os'))
            device.device_model = device_raw.get('model')
            device.last_seen = parse_date(device_raw.get('_as_of'))
            device.add_agent_version(version=device_raw.get('version'))

            services = []
            for network_interface in device_raw.get('network_interfaces'):
                ip = []
                subnet = []
                if network_interface.get('address') and network_interface.get('netmask'):
                    ip = [network_interface.get('address')]
                    subnet = [network_interface.get('address') + '/' + network_interface.get('netmask')]
                elif network_interface.get('address'):
                    ip = [network_interface.get('address')]

                device.add_nic(mac=network_interface.get('hwaddr'),
                               ips=ip,
                               subnets=subnet,
                               name=network_interface.get('name'),
                               speed=str(network_interface.get('speed')),
                               mtu=network_interface.get('mtu'),
                               gateway=network_interface.get('gateway'))

                if isinstance(network_interface.get('services'), list):
                    services.extend(network_interface.get('services'))
            for service in list(set(services)):  # No overlap data
                if isinstance(service, str):
                    device.add_service(name=service)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching PureStorageFlashArray Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching PureStorageFlashArray Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
