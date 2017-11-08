from services.axonius_fixture import axonius_fixture
from services.ad_service import ad_fixture
from services.epo_service import epo_fixture


def test_system_is_up(axonius_fixture):
    core = axonius_fixture['core']
    assert core.version().status_code == 200

    aggregator = axonius_fixture['aggregator']
    assert aggregator.version().status_code == 200

    db = axonius_fixture['db']
    print("system is up")


def test_ad_adapter_is_up(axonius_fixture, ad_fixture):
    print("Ad adapter is up")


def test_ad_adapter_responds_to_schema(axonius_fixture, ad_fixture):
    assert ad_fixture.schema().status_code == 200


def test_epo_adapter_is_up(axonius_fixture, epo_fixture):
    print("Epo adapter is up")


def test_epo_adapter_responds_to_schema(axonius_fixture, epo_fixture):
    assert epo_fixture.schema().status_code == 200
