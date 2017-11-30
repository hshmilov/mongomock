import pytest
from services.aws_service import aws_fixture

client_details = {
    "aws_access_key_id": "AKIAJOCJ5PGEAR6LNIFQ",
    "aws_secret_access_key": "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",
    "region_name": "us-east-2"
}

SOME_DEVICE_ID = 'i-0ec91cae8a42be974'


def test_adapter_is_up(axonius_fixture, aws_fixture):
    print("Ad adapter is up")


def test_adapter_responds_to_schema(axonius_fixture, aws_fixture):
    assert aws_fixture.schema().status_code == 200


def test_adapter_in_configs(axonius_fixture, aws_fixture):
    plugin_unique_name = aws_fixture.unique_name
    adapter = axonius_fixture.db.get_unique_plugin_config(
        plugin_unique_name)
    assert adapter['plugin_name'] == 'aws_adapter'


def test_registered(axonius_fixture, aws_fixture):
    assert aws_fixture.is_plugin_registered(axonius_fixture.core)


def test_fetch_devices(axonius_fixture, aws_fixture):
    client_id = client_details['aws_access_key_id']
    axonius_fixture.add_client_to_adapter(
        aws_fixture, client_details, client_id)
    axonius_fixture.assert_device_aggregated(
        aws_fixture, client_id, SOME_DEVICE_ID)


def test_restart(axonius_fixture, aws_fixture):
    axonius_fixture.restart_plugin(aws_fixture)
