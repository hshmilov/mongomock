import threading
from typing import TYPE_CHECKING

# https://stackoverflow.com/questions/39740632/python-type-hinting-without-cyclic-imports
import cachetools

if TYPE_CHECKING:
    from axonius.clients.azure.client import AzureCloudConnection


class AzureNetworkWatchersConnection:
    def __init__(self, client: 'AzureCloudConnection'):
        self.client = client

    @cachetools.cached(cachetools.TTLCache(maxsize=200, ttl=300), lock=threading.Lock())
    def get_all_azure_network_watchers_for_subscription(self, subscription_id: str):
        return list(self.client.rm_subscription_paginated_get(
            'providers/Microsoft.Network/networkWatchers',
            subscription_id,
            api_version='2020-05-01'
        ))

    @cachetools.cached(cachetools.TTLCache(maxsize=200, ttl=300), lock=threading.Lock())
    def get_all_azure_flow_logs_for_subscription(self, subscription_id: str):
        try:
            all_network_watchers = self.get_all_azure_network_watchers_for_subscription(subscription_id)
        except Exception as e:
            raise ValueError(
                f'Error getting all network watchers ("/proviers/Microsoft.Network/networkWatchers"): {str(e)}'
            )

        all_flow_logs = []

        for network_watcher in all_network_watchers:
            all_flow_logs.extend(
                list(
                    self.client.rm_paginated_get(
                        network_watcher['id'].strip('/') + '/flowLogs',
                        api_version='2017-09-01'
                    )
                )
            )

        return all_flow_logs
