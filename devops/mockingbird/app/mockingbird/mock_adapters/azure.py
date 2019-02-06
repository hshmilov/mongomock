import uuid

from mockingbird.commons import mock_utils
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from azure_adapter.service import AzureAdapter


class AzureAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            AzureAdapter,
            [MockNetworkDeviceProperties.AzureDevice], []
        )

    @staticmethod
    def new_device_adapter() -> AzureAdapter.MyDeviceAdapter:
        return AzureAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: AzureAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = f'/subscriptions/vms/{network_device.name}'
        device.os = network_device.os
        device.cloud_id = device.id
        device.cloud_provider = 'Azure'
        device.name = network_device.name

        ips = mock_utils.get_all_ips(network_device)
        if ips:
            device.add_nic(None, ips)

        device.vm_id = uuid.uuid4()

        yield device
