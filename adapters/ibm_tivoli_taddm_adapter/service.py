import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.mixins.configurable import Configurable
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_unix_timestamp
from axonius.fields import Field
from ibm_tivoli_taddm_adapter.client_id import get_client_id
from ibm_tivoli_taddm_adapter.connection import IBMTivoliTaddmConnection

logger = logging.getLogger(f'axonius.{__name__}')

TADDM_SSL_DEFAULT_PORT = 9431


class IbmTivoliTaddmAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        taddm_virtual = Field(bool, 'Is Virtual')
        taddm_virtual_machine_state = Field(int, 'Virtual Machine State')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('host'))

    def _connect_client(self, client_config):
        client_id = self._get_client_id(client_config)
        try:
            connection = IBMTivoliTaddmConnection(
                domain=client_config['host'],
                port=TADDM_SSL_DEFAULT_PORT,
                username=client_config['username'],
                password=client_config['password'],
                verify_ssl=client_config.get('verify_ssl', False),
            )
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as e:
            logger.error(f'Failed to connect to client {client_id}')
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        with client_data:
            yield from client_data.get_device_list(self.__fetch_size, self.__depth_size)

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {
                    'name': 'host',
                    'title': 'Host Address',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'Username',
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
            'required': ['host', 'username', 'password', 'verify_ssl'],
            'type': 'array'
        }

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements, invalid-name
    def create_device(self, device_raw):
        device = self._new_device_adapter()
        device_id = device_raw.get('guid')
        if not device_id:
            logger.error(f'No device id for {device_raw}')
            return None
        device_name = device_raw.get('displayName')  # this is not 'name'! name is something entirely else.
        if device_name:
            device.name = device_name
            device.id = f'{device_id}_{device_name}'
        else:
            device.id = device_id
        device.hostname = device_raw.get('fqdn')
        device.total_number_of_physical_processors = device_raw.get('CPUDiesInstalled')
        device.total_number_of_cores = device_raw.get('CPUCoresInstalled')
        memory_size_raw = device_raw.get('memorySize')
        if memory_size_raw:
            try:
                memory_size_raw = int(memory_size_raw) / (1024 ** 3)
                device.total_physical_memory = memory_size_raw
            except Exception:
                logger.error('problem setting memory size')

        for cpu_raw in (device_raw.get('CPU') or []):
            try:
                device.add_cpu(ghz=cpu_raw.get('CPUSpeed'), cores=cpu_raw.get('numCPUs'))
            except Exception:
                logger.exception(f'Could not add cpu {cpu_raw}')
        os_raw = device_raw.get('OSRunning')
        if os_raw:
            try:
                device.figure_os(os_raw.get('OSName', '') + ' ' + os_raw.get('OSVersion', ''))
                device.os.distribution = os_raw.get('OSVersion')
                device.os.kernel_version = os_raw.get('kernelVersion')
                word_size = os_raw.get('wordSize')
                if word_size in [32, 64]:
                    device.os.bitness = word_size
                for swap_file in (os_raw.get('pageSpace') or []):
                    try:
                        name = swap_file.get('name')
                        size = swap_file.get('size')
                        if size:
                            size = int(size) / (1024 ** 3)
                        else:
                            size = None
                        if name or size:
                            device.add_swap_file(name, size)
                    except Exception:
                        logger.exception(f'Problem parsing swap file {swap_file}')
                for software_raw in (os_raw.get('softwareComponents') or []):
                    try:
                        software_raw_vendor = software_raw.get('publisher')
                        software_raw_name = software_raw.get('name')
                        software_raw_version = software_raw.get('softwareVersion')
                        device.add_installed_software(
                            vendor=software_raw_vendor,
                            name=software_raw_name,
                            version=software_raw_version
                        )
                    except Exception:
                        logger.exception(f'Problem adding software version {software_raw}')
            except Exception:
                logger.exception(f'Problem parsing os related info {os_raw}')

        for fs_raw in (device_raw.get('fileSystems') or []):
            try:
                total_size = fs_raw.get('capacity')
                free_size = fs_raw.get('availableSpace')

                if total_size:
                    total_size = int(total_size) / 1024
                else:
                    total_size = None

                if free_size:
                    free_size = int(free_size) / 1024
                else:
                    free_size = None

                device.add_hd(
                    path=fs_raw.get('mountPoint'),
                    description=fs_raw.get('description'),
                    total_size=total_size,
                    free_size=free_size,
                    file_system=fs_raw.get('type')
                )
            except Exception:
                logger.exception(f'Problem parsing file system {fs_raw}')

        if isinstance(device_raw.get('virtual'), bool):
            device.taddm_virtual = device_raw.get('taddm_virtual')
        if isinstance(device_raw.get('virtualMachineState'), int):
            device.taddm_virtual_machine_state = device_raw.get('virtualMachineState')

        # Note that ipInterfaces was something wrong! it showed me 90 interfaces with different ip, this could be
        # interfaces this device is interacting with or something like this, so beware of that.
        device_ip = device_raw.get('contextIp')
        if device_ip:
            device.add_nic(None, [device_ip.strip()])

        last_modified_time = device_raw.get('lastModifiedTime')
        if last_modified_time:
            device.last_seen = parse_unix_timestamp(last_modified_time)
        device.set_raw(device_raw)
        return device

    def _parse_raw_data(self, devices_raw_data):
        for raw_device_data in iter(devices_raw_data):
            try:
                device = self.create_device(raw_device_data)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    def _on_config_update(self, config):
        logger.info(f'Loading TADDM config: {config}')
        self.__fetch_size = int(config['fetch_size'])
        self.__depth_size = int(config['depth_size'])

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_size',
                    'title': 'Fetch size (devices in each request)',
                    'type': 'number'
                },
                {
                    'name': 'depth_size',
                    'title': 'Depth size (information per each device)',
                    'type': 'number'
                }
            ],
            'required': [
                'fetch_size',
                'depth_size',
            ],
            'pretty_name': 'TADDM Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_size': 1,
            'depth_size': 1
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
