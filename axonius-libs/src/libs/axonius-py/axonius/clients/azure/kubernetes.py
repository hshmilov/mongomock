import threading
from typing import TYPE_CHECKING

# https://stackoverflow.com/questions/39740632/python-type-hinting-without-cyclic-imports
import cachetools

if TYPE_CHECKING:
    from axonius.clients.azure.client import AzureCloudConnection


class AzureKubernetesConnection:
    def __init__(self, client: 'AzureCloudConnection'):
        self.client = client

    @cachetools.cached(cachetools.TTLCache(maxsize=200, ttl=300), lock=threading.Lock())
    def get_all_azure_kubernetes_for_subscription(self, subscription_id: str):
        return list(self.client.rm_subscription_paginated_get(
            'providers/Microsoft.ContainerService/managedClusters',
            subscription_id,
            api_version='2020-04-01'
        ))
