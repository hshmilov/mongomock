from services.ad_service import ad_fixture


def test_ad_adapter_is_up(axonius_fixture, ad_fixture):
    print("Ad adapter is up")


def test_ad_adapter_responds_to_schema(axonius_fixture, ad_fixture):
    assert ad_fixture.schema().status_code == 200


def test_ad_adapter_in_configs(axonius_fixture, ad_fixture):
    plugin_unique_name = ad_fixture.unique_name
    adapter = axonius_fixture['db'].get_unique_plugin_config(
        plugin_unique_name)
    assert adapter['plugin_name'] == 'ad_adapter'


def test_registered(axonius_fixture, ad_fixture):
    assert ad_fixture.is_plugin_registered(axonius_fixture['core'])


def test_ad_restart(axonius_fixture, ad_fixture):
    ad_fixture.stop()
    ad_fixture.start()
    ad_fixture.wait_for_service()
    assert ad_fixture.is_plugin_registered(axonius_fixture['core'])
