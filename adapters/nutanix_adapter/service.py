import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from nutanix_adapter.connection import NutanixConnection
from nutanix_adapter.client_id import get_client_id
from nutanix_adapter.consts import VM_TYPE, HOST_TYPE

logger = logging.getLogger(f'axonius.{__name__}')


class NutanixAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        nutanix_type = Field(str, 'Nutanix Type', enum=[HOST_TYPE, VM_TYPE])
        host_uuid = Field(str, 'Host UUID')
        device_state = Field(str, 'Device State')
        block_location = Field(str, 'Block Location')

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
        connection = NutanixConnection(domain=client_config['domain'],
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
        The schema NutanixAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Nutanix Domain',
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

    def _create_host_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device.nutanix_type = HOST_TYPE
            device_id = device_raw.get('uuid')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.uuid = device_raw.get('uuid')
            device.name = device_raw.get('name')
            device.device_serial = device_raw.get('serial')
            device.device_state = device_raw.get('state')
            device.bios_version = device_raw.get('bios_version')
            device.block_location = device_raw.get('block_location')
            try:
                device.physical_location = (device_raw.get('position') or {}).get('physical_location')
            except Exception:
                logger.exception(f'Problem getting physical location')
            nics_raw = device_raw.get('nics_raw')
            if not nics_raw or not isinstance(nics_raw, list):
                nics_raw = []
            for nic_raw in nics_raw:
                try:
                    mac = nic_raw.get('mac_address')
                    if not mac:
                        mac = None
                    ips = []
                    if isinstance(device_raw.get('ipv4_addresses'), list):
                        ips.extend(device_raw.get('ipv4_addresses'))
                    if isinstance(device_raw.get('ipv6_addresses'), list):
                        ips.extend(device_raw.get('ipv6_addresses'))
                    if not ips:
                        ips = None
                    if mac or ips:
                        device.add_nic(mac=mac, ips=ips)
                except Exception:
                    logger.exception(f'Problem with nic raw  {nic_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Nutanix Device for {device_raw}')
            return None

    def _create_vm_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device.nutanix_type = VM_TYPE
            device_id = device_raw.get('uuid')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.uuid = device_raw.get('uuid')
            device.name = device_raw.get('name')
            vm_nics = device_raw.get('vm_nics')
            if not isinstance(vm_nics, list):
                vm_nics = []
            for vm_nic in vm_nics:
                try:
                    ips = vm_nic.get('ip_address').split(',') if vm_nic.get('ip_address') else None
                    mac = vm_nic.get('mac_address') if vm_nic.get('mac_address') else None
                    if ips or mac:
                        device.add_nic(ips=ips, mac=mac)
                except Exception:
                    logger.exception(f'Problem with nic {vm_nic}')
            device.host_uuid = device_raw.get('host_uuid')
            device.description = device_raw.get('description')
            device.figure_os(device_raw.get('guest_os'))
            if isinstance(device_raw.get('memory_mb'), int):
                device.total_physical_memory = device_raw.get('memory_mb') / 1024.0
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Nutanix Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            device = None
            if device_type == VM_TYPE:
                device = self._create_vm_device(device_raw)
            elif device == HOST_TYPE:
                device = self._create_host_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Virtualization, AdapterProperty.Assets]
