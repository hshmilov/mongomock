import random
import string

from mockingbird.commons import mock_utils
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
        device.name = device.id + '-' + network_device.name
        device.os = network_device.os
        device.cloud_id = device.id
        device.cloud_provider = 'AWS'

        ips = mock_utils.get_all_ips(network_device)
        if ips:
            device.add_nic(None, ips)

        yield device
