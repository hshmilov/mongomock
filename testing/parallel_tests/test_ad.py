import pytest
from services.adapters.ad_service import AdService, ad_fixture
from services.dns_conflicts_service import DnsConflictsService, dns_conflicts_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_helpers.utils import try_until_not_thrown
from test_helpers.machines import FAKE_DNS_IP

fakednsaddr = FAKE_DNS_IP

ad_client1_details = {
    "admin_password": "@vULuAZa5-MPxac6acw%ff-5H=bD)DQ;",
    "admin_user": "TestDomain\\Administrator",
    "dc_name": "10.0.229.30",
    "domain_name": "DC=TestDomain,DC=test",
    "query_password": "@vULuAZa5-MPxac6acw%ff-5H=bD)DQ;",
    "query_user": "TestDomain\\Administrator",
    "dns_server_address": fakednsaddr
}

ad_client2_details = {
    "admin_password": "&P?HBx-e3s",
    "admin_user": "TestSecDomain\\Administrator",
    "dc_name": "10.0.229.9",
    "domain_name": "DC=TestSecDomain,DC=test",
    "query_password": "&P?HBx-e3s",
    "query_user": "TestSecDomain\\Administrator",
    "dns_server_address": fakednsaddr
}

DEVICE_ID_FOR_CLIENT_1 = 'CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test'
DEVICE_ID_FOR_CLIENT_2 = 'CN=DESKTOP-GO8PIUL,CN=Computers,DC=TestSecDomain,DC=test'


class TestAdAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return AdService()

    @property
    def adapter_name(self):
        return 'ad_adapter'

    @property
    def some_client_id(self):
        return ad_client1_details['dc_name']

    @property
    def some_client_details(self):
        return ad_client1_details

    @property
    def some_device_id(self):
        return DEVICE_ID_FOR_CLIENT_1

    def test_fetch_devices(self):
        # Adding first client
        client_id_1 = ad_client1_details['dc_name']
        self.adapter_service.add_client(ad_client1_details)

        # Adding second client
        # client_id_2 = ad_client2_details['dc_name']
        # self.axonius_service.add_client_to_adapter(self.adapter_service, ad_client2_details)

        # Checking that we have devices from both clients
        self.axonius_service.assert_device_aggregated(self.adapter_service, client_id_1, DEVICE_ID_FOR_CLIENT_1)
        # self.axonius_service.assert_device_aggregated(self.adapter_service, client_id_2, DEVICE_ID_FOR_CLIENT_2)

    def test_ip_resolving(self):
        self.adapter_service.resolve_ip()
        self.axonius_service.aggregator.query_devices(adapter_id=self.adapter_service.unique_name)

        def assert_ip_resolved():
            interfaces = self.axonius_service.get_device_network_interfaces(self.adapter_service.unique_name,
                                                                            DEVICE_ID_FOR_CLIENT_1)
            assert len(interfaces) > 0

        try_until_not_thrown(50, 5, assert_ip_resolved)

    def test_dns_conflicts(self, dns_conflicts_fixture):
        dns_conflicts_fixture.activateable_start()
        dns_conflicts_fixture.find_conflicts()

        def has_ip_conflict_tag():
            dns_conflicts_fixture.find_conflicts()
            assert len(self.axonius_service.get_devices_with_condition({"tags.tagname": "IP_CONFLICT"})) > 0

        try_until_not_thrown(100, 5, has_ip_conflict_tag)
