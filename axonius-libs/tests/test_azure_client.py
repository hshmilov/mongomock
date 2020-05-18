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
    with azure_connection() as connection:
        yield connection


# pylint: disable=redefined-outer-name
def test_get_vms(azure_client):
    assert list(azure_client.compute.get_all_vms())


def test_get_tenant_name(azure_client):
    org = azure_client.get_organization_information()
    disply_name = org.get('displayName')
    assert disply_name


def test_azure_ad_get_guest_users(azure_client):
    guest_users = list(azure_client.ad.get_guest_users())
    jprint(guest_users)
    assert len(guest_users) > 0


def jprint(to_print):
    print(json.dumps(to_print, indent=4))


def main():
    with azure_connection() as client:
        jprint(client.graph_get('organization'))


if __name__ == '__main__':
    sys.exit(main())
