import pytest
from services.sentinelone_service import sentinelone_fixture
from test_helpers.utils import check_conf

client_details = {
    "SentinelOne_Domain": "axonius.sentinelone.net",
    "username": "ofri",
    "password": "ulcLZ54vVyHam11s7JHV"
}

SOME_DEVICE_ID = '5a2d57293be1ee5df1126a75'  # test-sentinelone-linux


def test_adapter_is_up(axonius_fixture, sentinelone_fixture):
    assert sentinelone_fixture.is_up()


def test_adapter_responds_to_schema(axonius_fixture, sentinelone_fixture):
    assert sentinelone_fixture.schema().status_code == 200


def test_adapter_in_configs(axonius_fixture, sentinelone_fixture):
    check_conf(axonius_fixture, sentinelone_fixture, "sentinelone_adapter")


def test_registered(axonius_fixture, sentinelone_fixture):
    assert sentinelone_fixture.is_plugin_registered(axonius_fixture.core)


@pytest.mark.skip(reason="Test is currently unstable")
def test_fetch_devices(axonius_fixture, sentinelone_fixture):
    axonius_fixture.clear_all_devices()
    client_id = client_details['SentinelOne_Domain']
    axonius_fixture.add_client_to_adapter(sentinelone_fixture, client_details)
    axonius_fixture.assert_device_aggregated(sentinelone_fixture, client_id, SOME_DEVICE_ID, 200)


def test_restart(axonius_fixture, sentinelone_fixture):
    axonius_fixture.restart_plugin(sentinelone_fixture)
