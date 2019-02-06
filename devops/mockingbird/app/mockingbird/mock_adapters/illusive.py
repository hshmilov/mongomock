
from mockingbird.commons import mock_utils
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from illusive_adapter.service import IllusiveAdapter


class IllusiveAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            IllusiveAdapter,
            [MockNetworkDeviceProperties.IllusiveDevice], []
        )

    @staticmethod
    def new_device_adapter() -> IllusiveAdapter.MyDeviceAdapter:
        return IllusiveAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: IllusiveAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = network_device.hostname
        device.hostname = network_device.hostname
        device.os = network_device.os

        ips = mock_utils.get_all_ips(network_device)
        if ips:
            device.add_nic(None, ips)

        yield device
