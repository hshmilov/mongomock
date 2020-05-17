from typing import TYPE_CHECKING

# https://stackoverflow.com/questions/39740632/python-type-hinting-without-cyclic-imports
if TYPE_CHECKING:
    from axonius.clients.azure.client import AzureCloudConnection


class AzureComputeConnection:
    def __init__(self, client: 'AzureCloudConnection'):
        self.client = client

    def get_all_vms(self):
        for vm in self.client.rm_paginated_get(
                f'subscriptions/{self.client.subscription}/providers/Microsoft.Compute/virtualMachines'):
            yield vm
