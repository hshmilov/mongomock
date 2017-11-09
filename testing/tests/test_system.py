from services.axonius_fixture import axonius_fixture
from services.ad_service import ad_fixture
from services.epo_service import epo_fixture


# todo: generalize the adapter/plugin specific tests

def test_system_is_up(axonius_fixture):
    core = axonius_fixture['core']
    assert core.version().status_code == 200

    aggregator = axonius_fixture['aggregator']
    assert aggregator.version().status_code == 200

    print("system is up")


def test_aggregator_in_configs(axonius_fixture):
    aggregator_config = axonius_fixture['db'].get_unique_plugin_config('aggregator_plugin_1')
    assert aggregator_config['plugin_name'] == 'aggregator'


# ad

def test_ad_adapter_is_up(axonius_fixture, ad_fixture):
    print("Ad adapter is up")


def test_ad_adapter_responds_to_schema(axonius_fixture, ad_fixture):
    assert ad_fixture.schema().status_code == 200


def test_ad_adapter_in_configs(axonius_fixture, ad_fixture):
    adapter = axonius_fixture['db'].get_unique_plugin_config('ad_adapter_1')
    assert adapter['plugin_name'] == 'ad_adapter'


# epo

def test_epo_adapter_is_up(axonius_fixture, epo_fixture):
    print("Epo adapter is up")


def test_epo_adapter_responds_to_schema(axonius_fixture, epo_fixture):
    assert epo_fixture.schema().status_code == 200


def test_epo_adapter_in_configs(axonius_fixture, epo_fixture):
    adapter = axonius_fixture['db'].get_unique_plugin_config('epo_adapter_1')
    assert adapter['plugin_name'] == 'epo_adapter'
