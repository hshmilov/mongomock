from services.ad_service import ad_fixture

ad_client_details = {
    "admin_password": "@vULuAZa5-MPxac6acw%ff-5H=bD)DQ;",
    "admin_user": "TestDomain\\Administrator",
    "dc_name": "10.0.229.30",
    "domain_name": "DC=TestDomain,DC=test",
    "query_password": "@vULuAZa5-MPxac6acw%ff-5H=bD)DQ;",
    "query_user": "TestDomain\\Administrator"
}

SOME_DEVICE_ID = 'CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test'


def test_adapter_is_up(axonius_fixture, ad_fixture):
    print("Ad adapter is up")


def test_adapter_responds_to_schema(axonius_fixture, ad_fixture):
    assert ad_fixture.schema().status_code == 200


def test_adapter_in_configs(axonius_fixture, ad_fixture):
    plugin_unique_name = ad_fixture.unique_name
    adapter = axonius_fixture.db.get_unique_plugin_config(
        plugin_unique_name)
    assert adapter['plugin_name'] == 'ad_adapter'


def test_registered(axonius_fixture, ad_fixture):
    assert ad_fixture.is_plugin_registered(axonius_fixture.core)


def test_fetch_devices(axonius_fixture, ad_fixture):
    client_id = ad_client_details['dc_name']
    axonius_fixture.add_client_to_adapter(
        ad_fixture, ad_client_details, client_id)
    axonius_fixture.assert_device_aggregated(
        ad_fixture, client_id, SOME_DEVICE_ID)


def test_restart(axonius_fixture, ad_fixture):
    axonius_fixture.restart_plugin(ad_fixture)
