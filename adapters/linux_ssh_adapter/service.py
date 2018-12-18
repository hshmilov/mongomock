import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from linux_ssh_adapter.connection import LinuxSshConnection
from linux_ssh_adapter.client_id import get_client_id
from linux_ssh_adapter.consts import HOSTNAME, USERNAME, PORT, PRIVATE_KEY, PASSWORD, DEFAULT_PORT

logger = logging.getLogger(f'axonius.{__name__}')


class LinuxSshAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return LinuxSshConnection.test_reachability(client_config[HOSTNAME], client_config.get(PORT, DEFAULT_PORT))

    def _connect_client(self, client_config):
        try:
            key = client_config.get(PRIVATE_KEY)
            if key:
                key = self._grab_file_contents(key)

            with LinuxSshConnection(hostname=client_config[HOSTNAME],
                                    port=client_config.get(PORT, DEFAULT_PORT),
                                    username=client_config[USERNAME],
                                    password=client_config.get(PASSWORD),
                                    key=key) as connection:
                return connection
        except Exception as e:
            message = 'Error connecting to client with host_name {0}, reason: {1}'.format(
                client_config['host_name'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific host_name

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(client_name)

    @staticmethod
    def _clients_schema():
        """
        The schema LinuxSshAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': HOSTNAME,
                    'title': 'Host Name',
                    'type': 'string'
                },
                {
                    'name': USERNAME,
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': PRIVATE_KEY,
                    'title': 'Private Key',
                    'description': 'SSH Private key for authentication',
                    'type': 'file'
                },
                {
                    'name': PORT,
                    'title': 'SSH Port',
                    'type': 'integer',
                    'default': DEFAULT_PORT,
                    'description': 'Protocol Port'
                },
            ],
            'required': [
                HOSTNAME,
                USERNAME
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        device = self._new_device_adapter()
        for command in devices_raw_data:
            command.parse()
            command.to_axonius(device)
        yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
