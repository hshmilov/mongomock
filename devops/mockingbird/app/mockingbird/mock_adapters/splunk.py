from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from splunk_adapter.service import SplunkAdapter


class SplunkAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            SplunkAdapter,
            [MockNetworkDeviceProperties.SplunkDevice], []
        )

    @staticmethod
    def new_device_adapter() -> SplunkAdapter.MyDeviceAdapter:
        return SplunkAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: SplunkAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = network_device.hostname
        device.hostname = network_device.hostname
        device.network_interfaces = network_device.network_interfaces

        yield device
