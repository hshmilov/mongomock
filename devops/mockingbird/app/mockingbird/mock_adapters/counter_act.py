import random
import uuid

from axonius.devices.device_adapter import AGENT_NAMES
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from counter_act_adapter.service import CounterActAdapter


class CounterActAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            CounterActAdapter,
            [MockNetworkDeviceProperties.CounteractDevice], []
        )

    @staticmethod
    def new_device_adapter() -> CounterActAdapter.MyDeviceAdapter:
        return CounterActAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: CounterActAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        if network_device.hostname:
            device.name = network_device.hostname.upper()
            device.hostname = f'{network_device.hostname}.{network_device.domain}'
            device.add_agent_version(agent=AGENT_NAMES.counter_act, version='11.0.03.0003 (x64)')
        device.id = f'counter_act_{uuid.uuid4()}'
        try:
            device.os = network_device.os
            device.os.build = None
        except Exception:
            pass

        device.domain = network_device.domain
        device.part_of_domain = network_device.part_of_domain
        device.network_interfaces = network_device.network_interfaces

        device.total_physical_memory = network_device.total_physical_memory
        device.free_physical_memory = network_device.free_physical_memory
        device.total_number_of_cores = network_device.total_number_of_cores

        device.open_ports = network_device.open_ports
        device.installed_software = network_device.installed_software

        os_type = None
        try:
            os_type = network_device.os.type.capitalize()
        except Exception:
            pass

        if network_device.hostname:
            device.in_groups = ['CounterACT Devices - CORP']
            if random.randint(1, 10) <= 8:
                device.in_groups.append('Compliant Host')
            if os_type:
                device.fingerprint = f'{os_type} Machine'
                device.in_groups.append(f'{os_type} Devices - CORP')

        yield device
