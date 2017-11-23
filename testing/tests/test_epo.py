from services.epo_service import epo_fixture
import json
from test_helpers.utils import try_until_not_thrown

epo_client_details = {
    "admin_password": "nTiQHY3Cw6rE",
    "admin_user": "admin",
    "host": "ec2-18-216-71-81.us-east-2.compute.amazonaws.com",
    "port": 8443,
    "query_user": "admin",
    "query_password": "nTiQHY3Cw6rE"
}

EPO_DEVICE_HOSTNAME = 'EC2AMAZ-0VJ3RSP'
EPO_AGENT_ID = 'F982D34B-A2DC-4BD2-AC9A-E2EDA0678899'


def test_epo_adapter_is_up(axonius_fixture, epo_fixture):
    print("Epo adapter is up")


def test_epo_adapter_responds_to_schema(axonius_fixture, epo_fixture):
    assert epo_fixture.schema().status_code == 200


def test_epo_adapter_in_configs(axonius_fixture, epo_fixture):
    plugin_unique_name = epo_fixture.unique_name
    adapter = axonius_fixture.db.get_unique_plugin_config(
        plugin_unique_name)
    assert adapter['plugin_name'] == 'epo_adapter'


def test_registered(axonius_fixture, epo_fixture):
    assert epo_fixture.is_plugin_registered(axonius_fixture.core)


def test_epo_restart(axonius_fixture, epo_fixture):
    epo_fixture.stop()
    epo_fixture.start()
    epo_fixture.wait_for_service()
    assert epo_fixture.is_plugin_registered(axonius_fixture.core)


def test_fetch_devices_from_client(axonius_fixture, epo_fixture):
    db = axonius_fixture.db
    clients = epo_fixture.add_client(db, epo_client_details)
    epo_host = epo_client_details['host']

    agg = axonius_fixture.aggregator
    assert agg.query_devices().status_code == 200  # ask agg to refresh devices ASAP
    assert epo_host in str(clients.content)

    devices_as_dict = epo_fixture.devices()
    assert epo_host in devices_as_dict

    devices_list = devices_as_dict[epo_host]['parsed']
    assert len(devices_list) == 1
    assert devices_list[0]['name'] == EPO_DEVICE_HOSTNAME

    def assert_epo_device_inserted():
        devices = axonius_fixture.get_device_by_name(
            epo_fixture.unique_name, EPO_DEVICE_HOSTNAME)
        assert len(devices) == 1

    try_until_not_thrown(30, 0.25, assert_epo_device_inserted)
