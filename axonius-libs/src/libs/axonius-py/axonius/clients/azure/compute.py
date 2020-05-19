from typing import TYPE_CHECKING

# https://stackoverflow.com/questions/39740632/python-type-hinting-without-cyclic-imports
if TYPE_CHECKING:
    from axonius.clients.azure.client import AzureCloudConnection


class AzureComputeConnection:
    def __init__(self, client: 'AzureCloudConnection'):
        self.client = client

    def get_all_vms(self, one_subscription=None):
        """
        :param one_subscription: If specified, brings from that subscription.
                                 otherwise brings from all accessible subscriptions
        :return:
        """
        subscriptions = [one_subscription] if one_subscription else self.client.all_subscriptions.keys()

        for subscription in subscriptions:
            for vm in self.client.rm_paginated_get(
                    f'subscriptions/{subscription}/providers/Microsoft.Compute/virtualMachines'):
                yield vm
