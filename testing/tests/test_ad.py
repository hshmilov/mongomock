from services.ad_service import ad_fixture
from test_helpers.utils import try_until_not_thrown, check_conf
from axonius.consts import AdapterConsts

ad_client1_details = {
    "admin_password": "@vULuAZa5-MPxac6acw%ff-5H=bD)DQ;",
    "admin_user": "TestDomain\\Administrator",
    "dc_name": "10.0.229.30",
    "domain_name": "DC=TestDomain,DC=test",
    "query_password": "@vULuAZa5-MPxac6acw%ff-5H=bD)DQ;",
    "query_user": "TestDomain\\Administrator"
}

ad_client2_details = {
    "admin_password": "&P?HBx-e3s",
    "admin_user": "TestSecDomain\\Administrator",
    "dc_name": "10.0.229.9",
    "domain_name": "DC=TestSecDomain,DC=test",
    "query_password": "&P?HBx-e3s",
    "query_user": "TestSecDomain\\Administrator"
}

DEVICE_ID_FOR_CLIENT_1 = 'CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test'
DEVICE_ID_FOR_CLIENT_2 = 'CN=DESKTOP-GO8PIUL,CN=Computers,DC=TestSecDomain,DC=test'


def test_adapter_is_up(axonius_fixture, ad_fixture):
    assert ad_fixture.is_up()


def test_adapter_responds_to_schema(axonius_fixture, ad_fixture):
    assert ad_fixture.schema().status_code == 200


def test_adapter_in_configs(axonius_fixture, ad_fixture):
    adapter_name = 'ad_adapter'
    check_conf(axonius_fixture, ad_fixture, adapter_name)


def test_registered(axonius_fixture, ad_fixture):
    assert ad_fixture.is_plugin_registered(axonius_fixture.core)


def test_fetch_devices(axonius_fixture, ad_fixture):
    axonius_fixture.clear_all_devices()
    # Adding first client
    client_id_1 = ad_client1_details['dc_name']
    axonius_fixture.add_client_to_adapter(
        ad_fixture, ad_client1_details)
    # Adding second client
    client_id_2 = ad_client2_details['dc_name']
    axonius_fixture.add_client_to_adapter(
        ad_fixture, ad_client2_details)

    # Checking that we have devices from both clients
    axonius_fixture.assert_device_aggregated(
        ad_fixture, client_id_1, DEVICE_ID_FOR_CLIENT_1)
    axonius_fixture.assert_device_aggregated(
        ad_fixture, client_id_2, DEVICE_ID_FOR_CLIENT_2)


def test_ip_resolving(axonius_fixture, ad_fixture):
    ad_fixture.post('resolve_ip', None, None)

    def assert_ip_resolved():
        axonius_fixture.trigger_aggregator()
        interfaces = axonius_fixture.get_device_network_interfaces(ad_fixture.unique_name, DEVICE_ID_FOR_CLIENT_1)
        assert len(interfaces) > 0

    try_until_not_thrown(10, 0.5, assert_ip_resolved)


def test_restart(axonius_fixture, ad_fixture):
    axonius_fixture.restart_plugin(ad_fixture)
