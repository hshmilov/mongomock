# THIS FILE IS NOT WORKING! It is a preparation for Azure REST Only client to be used by the compliance.
import datetime
import logging
from enum import Enum, auto

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


DEFAULT_API_VERSION = '2016-03-30'
DEFAULT_RESOURCE = 'https://management.azure.com'


class AzureClouds(Enum):
    Public = auto()
    Gov = auto()
    China = auto()
    Germany = auto()


AZURE_CLOUDS_LOGIN = {
    AzureClouds.Public: 'https://login.microsoftonline.com',
    AzureClouds.Gov: 'https://login.microsoftonline.us',
    AzureClouds.China: 'https://login.chinacloudapi.cn',
    AzureClouds.Germany: 'https://login.microsoftonline.de'
}

PAGINATION_LIMIT = 1000000      # protect from infinite loop


class AzureManagementConnection(RESTConnection):
    """ Regular Azure Management connection. supports Azure stack hub as well """

    def __init__(
            self,
            app_client_id: str,
            app_client_secret: str,
            app_tenant_id: str,
            subscription: str,
            cloud: AzureClouds = AzureClouds.Public,
            resource: str = None,
            **kwargs
    ):
        self._app_client_id = app_client_id
        self._app_client_secret = app_client_secret
        self._app_tenant_id = app_tenant_id
        self._subscription = subscription
        self._last_refresh = None
        self._expires_in = None

        if resource:
            self._resource = resource
        else:
            self._resource = DEFAULT_RESOURCE

        if cloud:
            self._cloud = cloud
        else:
            self._cloud = AzureClouds.Public

        super().__init__(self._resource,
                         headers={
                             'Content-Type': 'application/json',
                             'Accept': 'application/json'
                         },
                         **kwargs)

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return

        body_params = f'grant_type=client_credentials' \
            f'&client_id={self._app_client_id}' \
            f'&client_secret={self._app_client_secret}' \
            f'&resource={self._resource}'

        response = self._post(f'{AZURE_CLOUDS_LOGIN[self._cloud]}/{self._app_tenant_id}/oauth2/token',
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                              body_params=body_params,
                              force_full_url=True,
                              use_json_in_body=False)
        if 'access_token' not in response:
            raise RESTException(f'Invalid Response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._last_refresh = datetime.datetime.now()
        self._expires_in = int(response['expires_in']) - 60     # be on the safe side with 60 seconds less

    def _request(self, *args, **kwargs):
        self._refresh_token()
        return self._do_request(*args, **kwargs)

    def _paginated_request(self, method: str, url: str):
        page = 0
        force_full_url = False
        while page < PAGINATION_LIMIT:
            try:
                self._refresh_token()
                result = self._request(method, url, force_full_url=force_full_url)
                yield from (result.get('value') or [])
                url = result.get('nextLink')
                if not url:
                    break
                force_full_url = True
                page += 1
            except Exception:
                logger.exception(f'Failed fetching page {page} with url {url}')
                raise

    def _paginated_get(self, *args, **kwargs):
        yield from self._paginated_request('GET', *args, **kwargs)

    def _connect(self):
        if not self._app_client_id or not self._app_client_secret or not self._app_tenant_id:
            raise RESTException('No Client ID or Secret or Tenant ID')

        self._request(
            'GET',
            f'subscriptions/{self._subscription}/providers/Microsoft.Compute/'
            f'virtualMachines?api-version={DEFAULT_API_VERSION}'
        )

    @staticmethod
    def get_nic(url):
        return {}

    @staticmethod
    def get_instance_view(url):
        return {}

    def get_device_list(self):
        for vm in self._paginated_get(f'subscriptions/{self._subscription}/providers/'
                                      f'Microsoft.Compute/virtualMachines?api-version={DEFAULT_API_VERSION}'):
            # For each VM we have to do some more requests.
            # In the future this HAS to be async!
            try:
                vm['network_profile']['network_interfaces'] = [
                    self.get_nic(x['id']) for x in vm['network_profile']['network_interfaces']
                ]
            except Exception:
                logger.exception(f'Could not parse network interfaces')
            try:
                vm['instance_view'] = self.get_instance_view(vm)
            except Exception:
                logger.exception(f'Could not parse instance view')
            yield vm
