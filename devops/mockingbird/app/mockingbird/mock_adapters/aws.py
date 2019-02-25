import random
import string

from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from aws_adapter.service import AwsAdapter


class AwsAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            AwsAdapter,
            [MockNetworkDeviceProperties.AWSDevice], []
        )

    @staticmethod
    def new_device_adapter() -> AwsAdapter.MyDeviceAdapter:
        return AwsAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: AwsAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = 'i-' + ''.join(random.choices(string.hexdigits, k=16))
        device.name = network_device.name
        device.os = network_device.os
        device.cloud_id = device.id
        device.cloud_provider = 'AWS'
        device.network_interfaces = network_device.network_interfaces

        yield device
