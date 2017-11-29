from services.esx_service import esx_fixture

client_details = {
    "host": "vcenter",
    "user": "administrator@vsphere.local",
    "password": "Br!ng0rder",
    "verify_ssl": False
}

# vcenter vm
SOME_DEVICE_ID = '52e71bcb-db64-fe5e-40bf-8f5aa36f1e6b'


def test_adapter_is_up(axonius_fixture, esx_fixture):
    print("adapter is up")


def test_adapter_responds_to_schema(axonius_fixture, esx_fixture):
    assert esx_fixture.schema().status_code == 200


def test_adapter_in_configs(axonius_fixture, esx_fixture):
    plugin_unique_name = esx_fixture.unique_name
    adapter = axonius_fixture.db.get_unique_plugin_config(
        plugin_unique_name)
    assert adapter['plugin_name'] == 'esx_adapter'


def test_registered(axonius_fixture, esx_fixture):
    assert esx_fixture.is_plugin_registered(axonius_fixture.core)


def test_fetch_devices(axonius_fixture, esx_fixture):
    client_id = "{}/{}".format(client_details['host'], client_details['user'])
    axonius_fixture.add_client_to_adapter(
        esx_fixture, client_details, client_id)
    axonius_fixture.assert_device_aggregated(
        esx_fixture, client_id, SOME_DEVICE_ID)


def test_restart(axonius_fixture, esx_fixture):
    axonius_fixture.restart_plugin(esx_fixture)
