from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from esx_adapter.service import EsxAdapter


class EsxAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            EsxAdapter,
            [MockNetworkDeviceProperties.EsxDevice], []
        )

    @staticmethod
    def new_device_adapter() -> EsxAdapter.MyDeviceAdapter:
        return EsxAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: EsxAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = network_device.hostname
        device.hostname = network_device.hostname
        device.os = network_device.os
        device.os.build = None
        device.hard_drives = network_device.hard_drives
        device.name = (network_device.name or network_device.hostname)
        device.network_interfaces = network_device.network_interfaces
        device.total_physical_memory = network_device.total_physical_memory
        device.total_number_of_physical_processors = network_device.total_number_of_physical_processors

        yield device
