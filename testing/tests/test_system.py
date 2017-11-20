from services.ad_service import ad_fixture


# todo: generalize the adapter/plugin specific tests

def test_system_is_up(axonius_fixture):
    core = axonius_fixture['core']
    assert core.version().status_code == 200

    aggregator = axonius_fixture['aggregator']
    assert aggregator.version().status_code == 200

    print("system is up")


def test_aggregator_in_configs(axonius_fixture):
    aggregator = axonius_fixture['aggregator']
    plugin_unique_name = aggregator.unique_name
    aggregator_config = axonius_fixture['db'].get_unique_plugin_config(plugin_unique_name)
    assert aggregator_config['plugin_name'] == 'aggregator'
