from mockingbird.commons import mock_utils
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
        device.hard_drives = network_device.hard_drives
        device.name = (network_device.name or network_device.hostname)
        device.network_interfaces = network_device.network_interfaces

        yield device
