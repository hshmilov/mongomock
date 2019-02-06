import random

from uuid import uuid4
from datetime import datetime, timedelta

from axonius.devices.device_adapter import AdapterProperty
from mockingbird.commons import mock_utils
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.adapter_parser import AdapterParser
from qualys_scans_adapter.service import QualysScansAdapter


class QualysScansAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            QualysScansAdapter,
            [MockNetworkDeviceProperties.QualysScansDevice], []
        )

    @staticmethod
    def new_device_adapter() -> QualysScansAdapter.MyDeviceAdapter:
        return QualysScansAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def _parse_device(device: QualysScansAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        device.id = network_device.hostname
        device.name = network_device.hostname
        device.hostname = network_device.hostname
        device.os = network_device.os

        ips = mock_utils.get_all_ips(network_device)
        if ips:
            device.add_nic(None, ips)

        device.adapter_properties = [AdapterProperty.Vulnerability_Assessment.name, AdapterProperty.Agent.name]
        device.physical_location = network_device.physical_location

        # to be fixed - should be a property of the network
        device.agent_version = '1.6.4.9' if random.randint(1, 100) <= 5 else '1.4.5.232'  # 5% of not updated agent
        if device.last_seen:
            device.agent_status = 'STATUS_ACTIVE' \
                if device.last_seen + timedelta(days=30) > datetime.now() else 'STATUS_INACTIVE'
        else:
            device.agent_status = 'STATUS_INACTIVE'
        if random.randint(0, 9) < 3:
            device.add_qualys_vuln(vuln_id=uuid4(),
                                   last_found=datetime.now() - timedelta(days=random.randint(7, 14)),
                                   qid=uuid4(),
                                   first_found=datetime.now() - timedelta(days=random.randint(14, 21))
                                   )

        yield device
