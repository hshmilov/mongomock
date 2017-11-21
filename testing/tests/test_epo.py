from services.epo_service import epo_fixture
import json

epo_client_details = {
    "admin_password": "nTiQHY3Cw6rE",
    "admin_user": "admin",
    "host": "ec2-18-216-71-81.us-east-2.compute.amazonaws.com",
    "port": 8443,
    "query_user": "admin",
    "query_password": "nTiQHY3Cw6rE"
}


def test_epo_adapter_is_up(axonius_fixture, epo_fixture):
    print("Epo adapter is up")


def test_epo_adapter_responds_to_schema(axonius_fixture, epo_fixture):
    assert epo_fixture.schema().status_code == 200


def test_epo_adapter_in_configs(axonius_fixture, epo_fixture):
    plugin_unique_name = epo_fixture.unique_name
    adapter = axonius_fixture['db'].get_unique_plugin_config(
        plugin_unique_name)
    assert adapter['plugin_name'] == 'epo_adapter'


def test_registered(axonius_fixture, epo_fixture):
    assert epo_fixture.is_plugin_registered(axonius_fixture['core'])


def test_fetch_devices_from_client(axonius_fixture, epo_fixture):
    db = axonius_fixture['db']
    clients = epo_fixture.add_client(db, epo_client_details)
    assert epo_client_details['host'] in str(clients.content)
    devices = epo_fixture.devices()
    parsed = json.loads(devices.content)
    assert len(parsed) == 1
    assert parsed[0][0] == epo_client_details['host']
    assert parsed[0][1]['parsed'][0]['name'] == 'EC2AMAZ-0VJ3RSP'
