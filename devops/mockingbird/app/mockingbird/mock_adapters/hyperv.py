
from mockingbird.commons import mock_utils
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from hyper_v_adapter.service import HyperVAdapter


class HypervAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            HyperVAdapter,
            [MockNetworkDeviceProperties.HyperVDevice], []
        )

    @staticmethod
    def new_device_adapter() -> HyperVAdapter.MyDeviceAdapter:
        return HyperVAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: HyperVAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = network_device.hostname
        device.name = network_device.name + '-VM'
        device.os = network_device.os
        device.hard_drives = network_device.hard_drives
        device.network_interfaces = network_device.network_interfaces

        yield device
