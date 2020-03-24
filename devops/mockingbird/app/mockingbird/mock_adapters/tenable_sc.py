import uuid

from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from tenable_security_center_adapter.service import TenableSecurityCenterAdapter


class TenableScAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            TenableSecurityCenterAdapter,
            [MockNetworkDeviceProperties.TenableSC], []
        )

    @staticmethod
    def new_device_adapter() -> TenableSecurityCenterAdapter.MyDeviceAdapter:
        return TenableSecurityCenterAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: TenableSecurityCenterAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.hostname = f'{network_device.hostname}.{network_device.domain}'
        device.id = f'tenable_sc_{device.hostname}_{uuid.uuid4()}'

        device.network_interfaces = network_device.network_interfaces
        device.policy_name = '8271748d71-2a25-91fd-8f87a89b976c32-122319/Basic Network Scan'
        device.installed_software = network_device.installed_software

        try:
            for sw in network_device.installed_software:
                if sw.name == 'Adobe Flash Player 30 PPAPI':
                    for cve_id in [
                        'CVE-2019-7031',
                        'CVE-2019-7037',
                        'CVE-2019-7060',
                        'CVE-2019-16449',
                        'CVE-2019-19725',
                        'CVE-2019-16461'
                    ]:
                        device.add_vulnerable_software(
                            cve_id=cve_id
                        )
        except Exception:
            pass

        yield device
