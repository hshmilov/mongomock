import threading
import cachetools

# pylint: disable=W0231,W0223,C4002
from axonius.clients.azure.consts import AUTOMATION_API_VERSIION
from axonius.clients.rest.exception import RESTException


class AzureAutomationConnection:
    """
    This class is for fetching software updates configurations for subscription/resource_group combinations
    It's created once per tenant id and intended to work with multiple subscriptions.
    """

    def __init__(self, client: 'AzureCloudConnection'):
        """ Create a connection using an AzureCloudConnection client """
        self._client = client
        self._api_version = AUTOMATION_API_VERSIION

    @cachetools.cached(cachetools.TTLCache(maxsize=200, ttl=300), lock=threading.Lock())
    def get_all_automation_accounts_for_subscription(self, subscription_id):
        if not isinstance(subscription_id, str):
            raise TypeError(f'Unexpected type of subscription id: {str(type(subscription_id))}')
        try:
            with self._client:
                yield from self._client.rm_subscription_paginated_get(
                    url=f'providers/Microsoft.Automation/automationAccounts',
                    subscription=subscription_id,
                    api_version=self._api_version
                )
        except Exception as error:
            raise RESTException(f'Could not fetch the required resource:{str(error)}')

    @cachetools.cached(cachetools.TTLCache(maxsize=200, ttl=300), lock=threading.Lock())
    def get_update_configurations(
            self,
            subscription_id: str,
            automation_account_name: str,
            resource_group: str
    ):
        if not (subscription_id and isinstance(subscription_id, str)):
            raise TypeError(f'Unexpected type of subscription id: {str(type(subscription_id))}')
        if not (automation_account_name and isinstance(automation_account_name, str)):
            raise TypeError(f'Unexpected type of automation account name: {str(type(automation_account_name))}')
        if not (resource_group and isinstance(resource_group, str)):
            raise TypeError(f'Unexpected type of resource group: {str(type(resource_group))}')

        try:
            with self._client:
                yield from self._client.rm_subscription_paginated_get(
                    url=f'resourceGroups/{resource_group}/'
                        f'providers/Microsoft.Automation/'
                        f'automationAccounts/{automation_account_name}/'
                        f'softwareUpdateConfigurations',
                    subscription=subscription_id,
                    api_version=self._api_version
                )
        except Exception as error:
            raise RESTException(f'Could not fetch the required resource:{str(error)}')
