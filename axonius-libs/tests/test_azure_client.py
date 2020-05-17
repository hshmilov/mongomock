import json
import sys

import pytest

from axonius.clients.azure.client import AzureCloudConnection
from test_credentials.test_azure_credentials import client_details as azure_client_details


def azure_connection() -> AzureCloudConnection:
    return AzureCloudConnection(
        azure_client_details['client_id'],
        azure_client_details['client_secret'],
        azure_client_details['tenant_id'],
        azure_client_details['subscription_id'],
    )


@pytest.fixture(scope='module')
def azure_client() -> AzureCloudConnection:
    return azure_connection()


# pylint: disable=redefined-outer-name
def test_get_vms(azure_client):
    with azure_client:
        assert list(azure_client.compute.get_all_vms())


def test_get_tenants(azure_client):
    with azure_client:
        print(json.dumps(list(azure_client.get_tenants_list())))


def jprint(to_print):
    print(json.dumps(to_print, indent=4))


def main():
    with azure_connection() as client:
        jprint(list(client.get_tenants_list()))


if __name__ == '__main__':
    sys.exit(main())
