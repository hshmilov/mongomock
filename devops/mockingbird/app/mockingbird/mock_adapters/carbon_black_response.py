from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from carbonblack_response_adapter.service import CarbonblackResponseAdapter


class CarbonBlackResponseAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            CarbonblackResponseAdapter,
            [MockNetworkDeviceProperties.CarbonBlackResponseDevice], []
        )

    @staticmethod
    def new_device_adapter() -> CarbonblackResponseAdapter.MyDeviceAdapter:
        return CarbonblackResponseAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: CarbonblackResponseAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = network_device.hostname
        device.hostname = network_device.name
        if network_device.domain:
            device.hostname += f'.{network_device.domain}'
        device.os = network_device.os
        device.network_interfaces = network_device.network_interfaces
        device.hard_drives = network_device.hard_drives

        if not device.sensor_status:
            device.sensor_status = 'Online'

        if not device.build_version_string:
            device.build_version_string = '006.001.002.71109'

        if network_device.free_physical_memory and network_device.total_physical_memory and \
                (network_device.free_physical_memory / network_device.total_physical_memory) < 0.2:
            device.sensor_health_message = 'High memory usage'

        yield device
