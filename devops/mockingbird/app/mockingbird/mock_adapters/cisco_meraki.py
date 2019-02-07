from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from cisco_meraki_adapter.service import CiscoMerakiAdapter


class CiscoMerakiAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            CiscoMerakiAdapter,
            [MockNetworkDeviceProperties.CiscoMerakiDevice], []
        )

    @staticmethod
    def new_device_adapter() -> CiscoMerakiAdapter.MyDeviceAdapter:
        return CiscoMerakiAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: CiscoMerakiAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = f'cisco-meraki-{network_device.name}'
        device.name = network_device.name
        device.hostname = network_device.hostname
        device.network_interfaces = network_device.network_interfaces
        device.network_id = network_device.domain

        # Notice that device.device_type can be client device or cisco device, be sure to have at least one cisco
        # device in your network

        yield device
