import uuid

from mockingbird.commons import mock_utils
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from gce_adapter.service import GceAdapter


class GceAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            GceAdapter,
            [MockNetworkDeviceProperties.GCEDevice], []
        )

    @staticmethod
    def new_device_adapter() -> GceAdapter.MyDeviceAdapter:
        return GceAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: GceAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = str(uuid.uuid4()) + f'-{device.name}'
        device.cloud_provider = 'GCP'
        device.cloud_id = device.id
        device.hostname = network_device.hostname    # shouldn't be but is there for correlation
        device.os = network_device.os
        device.name = network_device.name

        ips = mock_utils.get_all_ips(network_device)
        if ips:
            device.add_nic(None, ips)

        yield device
