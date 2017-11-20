from services.epo_service import epo_fixture


def test_epo_adapter_is_up(axonius_fixture, epo_fixture):
    print("Epo adapter is up")


def test_epo_adapter_responds_to_schema(axonius_fixture, epo_fixture):
    assert epo_fixture.schema().status_code == 200


def test_epo_adapter_in_configs(axonius_fixture, epo_fixture):
    plugin_unique_name = epo_fixture.unique_name
    adapter = axonius_fixture['db'].get_unique_plugin_config(plugin_unique_name)
    assert adapter['plugin_name'] == 'epo_adapter'


def test_registered(axonius_fixture, epo_fixture):
    assert epo_fixture.is_plugin_registered(axonius_fixture['core'])
