import threading
from typing import TYPE_CHECKING

from urllib3.util.url import parse_url

# https://stackoverflow.com/questions/39740632/python-type-hinting-without-cyclic-imports
import cachetools

if TYPE_CHECKING:
    from axonius.clients.azure.client import AzureCloudConnection


class AzureKeyvaultConnection:
    def __init__(self, client: 'AzureCloudConnection'):
        self.client = client

    @cachetools.cached(cachetools.TTLCache(maxsize=200, ttl=300), lock=threading.Lock())
    def get_all_azure_keyvaults_for_subscription(self, subscription_id: str):
        return list(self.client.rm_subscription_paginated_get(
            f'providers/Microsoft.KeyVault/vaults', subscription_id, '2019-09-01'
        ))

    def get_all_keys_for_vault(self, vault_url: str):
        # https://testvault.vault.azure.net/something?a=2 becomes https://vault.azure.net
        resource = 'https://' + '.'.join(parse_url(vault_url).host.split('.')[1:])
        return list(
            self.client.rm_paginated_get(
                vault_url.rstrip('/') + '/keys',
                api_version='7.0',
                resource=resource,
                force_full_url=True
            )
        )

    def get_all_secrets_for_vault(self, vault_url: str):
        # https://testvault.vault.azure.net/something?a=2 becomes https://vault.azure.net
        resource = 'https://' + '.'.join(parse_url(vault_url).host.split('.')[1:])
        return list(
            self.client.rm_paginated_get(
                vault_url.rstrip('/') + '/secrets',
                api_version='7.0',
                resource=resource,
                force_full_url=True
            )
        )
