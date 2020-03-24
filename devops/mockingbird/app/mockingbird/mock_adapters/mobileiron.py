import random
import uuid

from axonius.devices.device_adapter import AGENT_NAMES
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from mobileiron_adapter.service import MobileironAdapter


class MobileironAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            MobileironAdapter,
            [MockNetworkDeviceProperties.MobileironDevice], []
        )

    @staticmethod
    def new_device_adapter() -> MobileironAdapter.MyDeviceAdapter:
        return MobileironAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: MobileironAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = uuid.uuid4()
        device.hostname = network_device.hostname
        device.os = network_device.os
        device.os.build = None
        device.email = network_device.email
        device.device_manufacturer = network_device.device_manufacturer
        device.device_model = network_device.device_model
        device.registration_state = 'ACTIVE'

        device.network_interfaces = network_device.network_interfaces

        device.uuid = uuid.uuid4()
        device.imei = random.randint(10 ** 12, 10 ** 13 - 1)
        device.add_agent_version(agent=AGENT_NAMES.mobileiron, version='9.8.0')

        yield device
