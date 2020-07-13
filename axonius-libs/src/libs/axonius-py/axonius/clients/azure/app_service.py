import threading
from typing import TYPE_CHECKING

# https://stackoverflow.com/questions/39740632/python-type-hinting-without-cyclic-imports
import cachetools

if TYPE_CHECKING:
    from axonius.clients.azure.client import AzureCloudConnection


class AzureAppServiceConnection:
    def __init__(self, client: 'AzureCloudConnection'):
        self.client = client

    @cachetools.cached(cachetools.TTLCache(maxsize=200, ttl=300), lock=threading.Lock())
    def get_all_azure_app_service_for_subscription(self, subscription_id: str):
        return list(self.client.rm_subscription_paginated_get(
            'providers/Microsoft.Web/sites',
            subscription_id,
            api_version='2019-08-01'
        ))

    @cachetools.cached(cachetools.TTLCache(maxsize=500, ttl=300), lock=threading.Lock())
    def get_config_for_azure_app_service(self, app_service_id: str):
        full_url = app_service_id.strip('/') + '/config/web'
        return self.client.rm_get(full_url, api_version='2017-08-01')
