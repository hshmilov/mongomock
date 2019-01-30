import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from solarwinds_orion_adapter.connection import SolarwindsConnection

logger = logging.getLogger(f'axonius.{__name__}')

# AX-969


class SolarwindsOrionAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        uri = Field(str, 'URI')
        ip_address_guid = Field(str, 'IP Address GUID')
        software_hardware_makeup = Field(str, 'Node Makeup')
        location = Field(str, 'Location')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        """
        :param client_config: client configuration includes password, username and domain
        :return: the domain, or patrolling ip address
        """
        return client_config['domain']

    def _test_reachability(self, client_config):
        # TODO: the port isn't documented anywhere but inside the connection class...
        return RESTConnection.test_reachability(client_config.get('domain'), 17778)

    def _connect_client(self, client_config):
        """
        Creates a solarwinds connection by creating an instance of Solarwinds Connection
        :param client_config: client configuration includes password, username and domain
        :return: instance of Solarwinds connection
        """

        try:
            connection = SolarwindsConnection(domain=client_config['domain'],
                                              username=client_config['username'],
                                              password=client_config['password'],
                                              verify_ssl=client_config['verify_ssl'])

            connection.connect()
            return connection
        except Exception as e:
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get a list of all of the devices used by the client
        :param client_name:
        :param session: instance of SolarWinds connection
        :return: device list of the patrolling user's devices
        """
        client_data.connect()
        yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        Denotes the clients schema to be used for the adapter.
        :return:
        """

        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'IP Address',
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
                }
            ],
            'required': [
                'domain',
                'username',
                'password'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        """
        Parses through the raw device list and creates new devices
        to be displayed on the Axonius site.
        :param raw_data: the list of devices that the system patrols
        :return:
        """
        for raw_device_data in iter(devices_raw_data):
            try:
                device = self._new_device_adapter()

                # NodeID is the unique identifier over time
                id_check = raw_device_data.get('NodeID')
                if not id_check:
                    logger.error(f'ID coming from Solarwinds does not have an ID on device {raw_device_data}')
                    continue
                else:
                    device.id = str(id_check)
                    device.name = raw_device_data.get('NodeName')
                    device.description = raw_device_data.get('Description')
                    available_memory_gb = None
                    used_memory_gb = None
                    try:
                        if raw_device_data.get('MemoryAvailable'):
                            available_memory_bytes = float(raw_device_data.get('MemoryAvailable'))
                            available_memory_gb = available_memory_bytes / (1024 ** 3)
                            device.free_physical_memory = available_memory_gb
                    except Exception:
                        logger.exception(f'No value for the float for {raw_device_data}')
                    try:
                        if raw_device_data.get('MemoryUsed'):
                            used_memory_bytes = float(raw_device_data.get('MemoryUsed'))
                            used_memory_gb = used_memory_bytes / (1024 ** 3)
                    except Exception:
                        logger.exception(f'No value for the float for {raw_device_data}')

                    try:
                        if available_memory_gb and used_memory_gb:
                            device.total_physical_memory = available_memory_gb + used_memory_gb
                    except Exception:
                        logger.exception(f'Either memory used or available memory does not exist in {raw_device_data}')

                    device.physical_memory_percentage = raw_device_data.get('PercentMemoryUsed')
                    device.figure_os(raw_device_data.get('NodeDescription'))
                    try:
                        if raw_device_data.get('CPUCount'):
                            device.add_cpu(cores=int(raw_device_data.get('CPUCount')))
                    except Exception:
                        logger.exception(f'Either no value or illegal cast to integer for {raw_device_data}')
                    device.uri = raw_device_data.get('Uri')
                    device.ip_address_guid = raw_device_data.get('IPAddressGUID')

                    mac_addresses = raw_device_data.get('MacAddresses')
                    ip_address = raw_device_data.get('IPAddress')

                    if ip_address:
                        ip_address = [ip_address]

                    if mac_addresses and isinstance(mac_addresses, list):
                        for address in mac_addresses:
                            try:
                                if ip_address:
                                    device.add_nic(mac=address, ips=ip_address)
                            except Exception:
                                logger.exception(f'Faulty mac address in the server for {raw_device_data}')

                    device.software_hardware_makeup = raw_device_data.get('NodeDescription')
                    device.location = raw_device_data.get('Location')
                device.set_raw(raw_device_data)
                yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

        logger.info('Finished parsing all of the raw devices')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
