from axonius.devices.device_adapter import AGENT_NAMES
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from eclypsium_adapter.service import EclypsiumAdapter


class EclypsiumAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            EclypsiumAdapter,
            [MockNetworkDeviceProperties.EclypsiumDevice], []
        )

    @staticmethod
    def new_device_adapter() -> EclypsiumAdapter.MyDeviceAdapter:
        return EclypsiumAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: EclypsiumAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = f'eclypsium_{network_device.name}'
        device.os = network_device.os
        device.os.build = None
        device.hostname = network_device.hostname
        device.network_interfaces = network_device.network_interfaces

        device.device_model = network_device.device_model
        device.device_manufacturer = network_device.device_manufacturer
        device.add_agent_version(AGENT_NAMES.eclypsium, version='1.8.0')

        yield device
