from mockingbird.commons import mock_utils
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from chef_adapter.service import ChefAdapter


class ChefAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            ChefAdapter,
            [MockNetworkDeviceProperties.ChefDevice], []
        )

    @staticmethod
    def new_device_adapter() -> ChefAdapter.MyDeviceAdapter:
        return ChefAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: ChefAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = network_device.hostname
        device.name = network_device.name
        device.hostname = network_device.hostname
        device.os = network_device.os
        device.network_interfaces = network_device.network_interfaces
        device.total_physical_memory = network_device.total_physical_memory
        device.free_physical_memory = network_device.free_physical_memory
        device.hard_drives = network_device.hard_drives
        device.installed_software = network_device.installed_software
        device.device_manufacturer = network_device.device_manufacturer
        device.total_number_of_cores = network_device.total_number_of_cores
        device.total_number_of_physical_processors = network_device.total_number_of_physical_processors
        device.swap_total = network_device.swap_total
        device.swap_free = network_device.swap_free

        yield device
