import uuid

from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from mockingbird.commons import mock_utils
from epo_adapter.service import EpoAdapter


class EpoAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            EpoAdapter,
            [MockNetworkDeviceProperties.EpoDevice], []
        )

    @staticmethod
    def new_device_adapter() -> EpoAdapter.MyDeviceAdapter:
        return EpoAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: EpoAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.hostname = network_device.hostname
        device.id = f'epo_{device.hostname}_{uuid.uuid4()}'
        device.name = device.hostname
        device.os = network_device.os
        device.hard_drives = network_device.hard_drives
        device.domain = network_device.domain
        device.part_of_domain = network_device.part_of_domain

        ips = mock_utils.get_all_ips(network_device)
        if ips:
            device.add_nic(None, ips)

        device.total_physical_memory = network_device.total_physical_memory
        device.free_physical_memory = network_device.free_physical_memory
        device.total_number_of_cores = network_device.total_number_of_cores

        yield device
