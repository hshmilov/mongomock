from services.esx_service import esx_fixture
import pytest
from test_helpers.utils import check_conf

client_details = [
    ({
        "host": "vcenter.axonius.lan",
        "user": "administrator@vsphere.local",
        "password": "Br!ng0rder",
        "verify_ssl": False
    }, '52e71bcb-db64-fe5e-40bf-8f5aa36f1e6b'),
    # This vcenter is currently not active!!! we should return it as soon as it becomes active again
    # ({
    #     "host": "vcenter51.axonius.lan",
    #     "user": "root",
    #     "password": "vmware",
    #     "verify_ssl": False
    # }, "525345eb-51ef-f4d7-85bb-08e521b94528"),
    ({
        "host": "vcenter55.axonius.lan",
        "user": "root",
        "password": "vmware",
        "verify_ssl": False
    }, "525d738d-c18f-ed57-6059-6d3378a61442")]

# vcenter vm
SOME_DEVICE_ID = '52e71bcb-db64-fe5e-40bf-8f5aa36f1e6b'


def test_adapter_is_up(axonius_fixture, esx_fixture):
    assert esx_fixture.is_up()


def test_adapter_responds_to_schema(axonius_fixture, esx_fixture):
    assert esx_fixture.schema().status_code == 200


def test_adapter_in_configs(axonius_fixture, esx_fixture):
    check_conf(axonius_fixture, esx_fixture, "esx_adapter")


def test_registered(axonius_fixture, esx_fixture):
    assert esx_fixture.is_plugin_registered(axonius_fixture.core)


def test_fetch_devices(axonius_fixture, esx_fixture):
    axonius_fixture.clear_all_devices()

    for client, some_device_id in client_details:
        client_id = "{}/{}".format(client['host'], client['user'])
        axonius_fixture.add_client_to_adapter(esx_fixture, client)
        axonius_fixture.assert_device_aggregated(esx_fixture, client_id, some_device_id)


def test_restart(axonius_fixture, esx_fixture):
    axonius_fixture.restart_plugin(esx_fixture)
