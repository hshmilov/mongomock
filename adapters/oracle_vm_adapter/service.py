import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.clients.rest.exception import RESTException
from axonius.clients.rest.connection import RESTConnection
from oracle_vm_adapter.connection import OracleVmConnection
from oracle_vm_adapter.consts import SERVERS_KEY_WORD, VMS_KEY_WORD

logger = logging.getLogger(f'axonius.{__name__}')


class OracleVmAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Device Type', enum=['OracleServer', 'VMMachine'])
        run_state = Field(str, 'Run State')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = OracleVmConnection(domain=client_config['domain'],
                                            verify_ssl=client_config['verify_ssl'],
                                            username=client_config['username'],
                                            password=client_config['password'])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Infoblox domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Infoblox connection

        :return: A json with all the attributes returned from the Infoblox Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema OracleVmAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'OracleVm Domain',
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
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def __create_server_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = (device_raw.get('id') or {}).get('value')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')
            device.name = device_raw.get('name')
            device.run_state = device_raw.get('serverRunState')
            ips = device_raw.get('ipAddress').split(',') if device_raw.get('ipAddress') else None
            if ips:
                device.add_nic(None, ips)
            device.description = device_raw.get('description')
            try:
                bios_version = (device_raw.get('biosVendor') or '') + ' ' + (device_raw.get('biosVersion') or '')
                if bios_version and bios_version.strip():
                    device.bios_version = bios_version
            except Exception:
                logger.exception(f'Problem getting bios version for {device_raw}')
            ram_mb = device_raw.get('memory')
            if isinstance(ram_mb, int):
                device.total_physical_memory = ram_mb / 1024.0
            usuable_mb = device_raw.get('usableMemory')
            if isinstance(usuable_mb, int):
                device.free_physical_memory = usuable_mb / 1024.0
            device.hostname = device_raw.get('hostname')
            device.device_serial = device_raw.get('serialNumber')
            device.device_manufacturer = device_raw.get('manufacturer')
            device.device_type = 'OracleServer'
            etherent_ports_data = device_raw.get('ethernet_ports_data')
            if not isinstance(etherent_ports_data, list):
                etherent_ports_data = []
            for ethernet_port_data in etherent_ports_data:
                try:
                    mac_address = ethernet_port_data.get('macAddress') if ethernet_port_data.get('macAddress') else None
                    ip_addresses = ethernet_port_data.get('ipaddresses').split(
                        ',') if ethernet_port_data.get('ipaddresses') else None
                    if mac_address or ip_addresses:
                        device.add_nic(mac_address, ip_addresses)
                except Exception:
                    logger.exception(f'Problem adding nic from ethernet port {ethernet_port_data}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching OracleVm Device {device_raw}')
            return None

    def __create_vm_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = (device_raw.get('id') or {}).get('value')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')
            device.name = device_raw.get('name')
            run_state = device_raw.get('vmRunState')
            if str(run_state).upper() == 'TEMPLATE':
                return None
            device.run_state = run_state
            device.description = device_raw.get('description')
            device.figure_os(device_raw.get('osType'))
            device.device_type = 'VMMachine'
            ram_mb = device_raw.get('currentMemory')
            if isinstance(ram_mb, int):
                device.total_physical_memory = ram_mb / 1024.0
            virtual_nics_data = device_raw.get('virtual_nics_data')
            if not isinstance(virtual_nics_data, list):
                virtual_nics_data = []
            for virtual_nic_data in virtual_nics_data:
                try:
                    mac_address = virtual_nic_data.get('macAddress') if virtual_nic_data.get('macAddress') else None
                    ip_addresses = virtual_nic_data.get('ipAddresses') if virtual_nic_data.get('ipAddresses') else None
                    if not isinstance(ip_addresses, list):
                        ip_addresses = None
                    if mac_address or ip_addresses:
                        device.add_nic(mac_address, ip_addresses)
                except Exception:
                    logger.exception(f'Problem adding nic from virtual nic {virtual_nic_data}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching OracleVm Device {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_type, device_raw in devices_raw_data:
            device = None
            if device_type == VMS_KEY_WORD:
                device = self.__create_vm_device(device_raw)
            if device_type == SERVERS_KEY_WORD:
                device = self.__create_server_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Virtualization]
