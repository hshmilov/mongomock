import random

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
        device.os.build = None
        device.network_interfaces = network_device.network_interfaces
        device.installed_software = network_device.installed_software
        device.security_patches = network_device.security_patches
        device.total_physical_memory = network_device.total_physical_memory
        device.total_number_of_physical_processors = network_device.total_number_of_physical_processors
        device.boot_time = network_device.boot_time
        device.last_used_users = network_device.last_used_users
        device.bios_serial = network_device.bios_serial

        if network_device.last_used_users:
            device.top_user = network_device.last_used_users[0]

        device.sccm_type = 'x64-based PC'
        device.resource_id = random.randint(100000, 999999)
        device.collections = ['All Systems', 'All Desktop and Server Clients', 'RWA']
        yield device
