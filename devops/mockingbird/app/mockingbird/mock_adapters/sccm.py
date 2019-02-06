from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from sccm_adapter.service import SccmAdapter


class SccmAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            SccmAdapter,
            [MockNetworkDeviceProperties.SccmDevice], []
        )

    @staticmethod
    def new_device_adapter() -> SccmAdapter.MyDeviceAdapter:
        return SccmAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: SccmAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        org_to_ad_format = ','.join(f'DC={org_part}' for org_part in network_device.domain.split('.'))
        ou = 'Domain Controllers' if device.ad_is_dc is True else 'Computers'
        device.id = f'CN={network_device.hostname},OU={ou},{org_to_ad_format}'  # Same as in AD
        device.hostname = f'{network_device.hostname}.{network_device.domain}'.upper()
        device.domain = network_device.domain
        device.part_of_domain = network_device.part_of_domain
        device.os = network_device.os
        device.network_interfaces = network_device.network_interfaces
        device.installed_software = network_device.installed_software
        device.total_physical_memory = network_device.total_physical_memory
        yield device
