from services.epo_service import epo_fixture

epo_client_details = {
    "admin_password": "6c=xz@OACxaefu)h38MFLD%dpiTeQu$=",
    "admin_user": "administrator",
    "host": "10.0.255.180",
    "port": 8443,
    "query_user": "administrator",
    "query_password": "6c=xz@OACxaefu)h38MFLD%dpiTeQu$="
}

SOME_DEVICE_ID = '6D57ECC5-88FA-4B77-BB7C-76D1EB7AEE4B'


def test_adapter_is_up(axonius_fixture, epo_fixture):
    print("Epo adapter is up")


def test_adapter_responds_to_schema(axonius_fixture, epo_fixture):
    assert epo_fixture.schema().status_code == 200


def test_adapter_in_configs(axonius_fixture, epo_fixture):
    plugin_unique_name = epo_fixture.unique_name
    adapter = axonius_fixture.db.get_unique_plugin_config(
        plugin_unique_name)
    assert adapter['plugin_name'] == 'epo_adapter'


def test_registered(axonius_fixture, epo_fixture):
    assert epo_fixture.is_plugin_registered(axonius_fixture.core)


def test_fetch_devices(axonius_fixture, epo_fixture):
    client_id = epo_client_details['host']
    axonius_fixture.add_client_to_adapter(
        epo_fixture, epo_client_details, client_id)
    axonius_fixture.assert_device_aggregated(
        epo_fixture, client_id, SOME_DEVICE_ID)


def test_restart(axonius_fixture, epo_fixture):
    axonius_fixture.restart_plugin(epo_fixture)
