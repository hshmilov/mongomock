import random

from mockingbird.commons import mock_utils
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from tanium_adapter.service import TaniumAdapter


class TaniumAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            TaniumAdapter,
            [MockNetworkDeviceProperties.TaniumDevice], []
        )

    @staticmethod
    def new_device_adapter() -> TaniumAdapter.MyDeviceAdapter:
        return TaniumAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: TaniumAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = network_device.hostname
        device.hostname = network_device.hostname
        device.os = network_device.os

        ips = mock_utils.get_all_ips(network_device)
        if ips:
            device.add_nic(None, ips)

        # to be fixed - should be part of the network but we leave it here for now
        device.agent_version = '7.2' if random.randint(0, 10) < 10 else '6.0'  # 10% of not updated agent
        yield device
