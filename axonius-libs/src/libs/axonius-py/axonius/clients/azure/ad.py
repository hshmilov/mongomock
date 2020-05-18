from typing import TYPE_CHECKING

# https://stackoverflow.com/questions/39740632/python-type-hinting-without-cyclic-imports
if TYPE_CHECKING:
    from axonius.clients.azure.client import AzureCloudConnection


class AzureADConnection:
    def __init__(self, client: 'AzureCloudConnection'):
        self.client = client

    def get_total_users_count(self):
        return len(list(self.client.graph_paginated_get('users', api_select='id')))

    def get_guest_users(self):
        yield from self.client.graph_paginated_get(
            'users',
            api_filter='userType eq \'Guest\''
        )
