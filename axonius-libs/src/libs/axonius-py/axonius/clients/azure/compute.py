import threading
from typing import TYPE_CHECKING

# https://stackoverflow.com/questions/39740632/python-type-hinting-without-cyclic-imports
import cachetools

if TYPE_CHECKING:
    from axonius.clients.azure.client import AzureCloudConnection


class AzureComputeConnection:
    def __init__(self, client: 'AzureCloudConnection'):
        self.client = client

    @cachetools.cached(cachetools.TTLCache(maxsize=200, ttl=300), lock=threading.Lock())
    def get_all_vms(self, one_subscription=None):
        """
        :param one_subscription: If specified, brings from that subscription.
                                 otherwise brings from all accessible subscriptions
        :return:
        """
        subscriptions = [one_subscription] if one_subscription else self.client.all_subscriptions.keys()

        all_vms = []
        for subscription in subscriptions:
            for vm in self.client.rm_subscription_paginated_get(
                    'providers/Microsoft.Compute/virtualMachines',
                    subscription,
                    api_version='2020-06-01'
            ):
                all_vms.append(vm)

        return all_vms

    @cachetools.cached(cachetools.TTLCache(maxsize=200, ttl=300), lock=threading.Lock())
    def get_all_disks(self, subscription_id: str):
        return list(
            self.client.rm_subscription_paginated_get(
                'providers/Microsoft.Compute/disks',
                subscription_id,
                '2020-05-01'
            )
        )
