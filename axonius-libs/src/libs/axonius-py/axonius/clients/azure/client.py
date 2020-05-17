# pylint: disable=access-member-before-definition
# THIS FILE IS NOT WORKING! It is a preparation for Azure REST Only client to be used by the compliance.
import datetime
import logging
from collections import namedtuple

import adal

from axonius.clients.azure.compute import AzureComputeConnection
from axonius.clients.azure.consts import AzureStackHubProxySettings, PAGINATION_LIMIT, AzureClouds
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


DEFAULT_API_VERSION = '2016-03-30'


AzureCloudEndpointsTuple = namedtuple(
    'CloudEndpoints', ['management_url', 'ad_graph_url', 'graph_url', 'login_url', 'resource']
)

AZURE_CLOUD_ENDPOINTS = {
    AzureClouds.Public: AzureCloudEndpointsTuple(
        management_url='https://management.azure.com',
        ad_graph_url='https://graph.windows.net/',
        graph_url='https://graph.microsoft.com/',
        login_url='https://login.microsoftonline.com',
        resource='https://management.core.windows.net/'
    ),
    AzureClouds.Gov: AzureCloudEndpointsTuple(
        management_url='https://management.usgovcloudapi.net',
        ad_graph_url='https://graph.windows.net/',
        graph_url='https://graph.microsoft.us/',
        login_url='https://login.microsoftonline.us',
        resource='https://management.core.usgovcloudapi.net/'
    ),
    AzureClouds.China: AzureCloudEndpointsTuple(
        management_url='https://management.chinacloudapi.cn',
        ad_graph_url='https://graph.chinacloudapi.cn/',
        graph_url='https://microsoftgraph.chinacloudapi.cn/',
        login_url='https://login.chinacloudapi.cn',
        resource='https://management.core.chinacloudapi.cn/'
    ),
    AzureClouds.Germany: AzureCloudEndpointsTuple(
        management_url='https://management.microsoftazure.de',
        ad_graph_url='https://graph.cloudapi.de/',
        graph_url='https://graph.microsoft.de/',
        login_url='https://login.microsoftonline.de',
        resource='https://management.core.cloudapi.de/'
    )
}

DOD_GRAPH_URL = 'https://dod-graph.microsoft.us'


# pylint: disable=too-many-instance-attributes, too-many-arguments
class AzureCloudConnection(RESTConnection):
    """ Regular Azure Management connection. supports Azure stack hub as well """

    def __init__(
            self,
            app_client_id: str,
            app_client_secret: str,
            tenant_id: str,
            subscription: str,
            cloud: AzureClouds = AzureClouds.Public,
            management_url: str = None,   # Set a different base-url for azure-stack-hub
            resource: str = None,   # Set a different resource for azure-stack-hub
            azure_stack_hub_proxy_settings: AzureStackHubProxySettings = None,
            is_azure_ad_b2c: bool = False,
            is_dod_graph: bool = None,
            **kwargs
    ):
        self._app_client_id = app_client_id
        self._app_client_secret = app_client_secret
        self.tenant_id = tenant_id
        self.subscription = subscription
        self._azure_stack_hub_proxy_settings = azure_stack_hub_proxy_settings
        self.is_azure_ad_b2c = is_azure_ad_b2c

        self._mgmt_token_last_refresh = None
        self._mgmt_token_expires_in = None
        self._mgmt_token = None
        self._graph_token_last_refresh = None
        self._graph_token_expires_in = None
        self._graph_token = None

        if cloud:
            self._cloud = cloud
        else:
            self._cloud = AzureClouds.Public

        logger.info(f'Using cloud {str(self._cloud)}')

        self._management_url, self._ad_graph_url, self._graph_url, self._auth_url, self._resource = \
            AZURE_CLOUD_ENDPOINTS[self._cloud]

        if self._cloud == AzureClouds.Gov and is_dod_graph:
            self._graph_url = DOD_GRAPH_URL

        if management_url:
            logger.info(f'Custom Management URL: {management_url}')
            self._management_url = management_url

        if resource:
            logger.info(f'Custom Resource: {resource}')
            self._resource = resource

        self._auth_alternative_proxies = None
        self._mgmt_url_alternative_proxies = None

        if self._azure_stack_hub_proxy_settings in [AzureStackHubProxySettings.DoNotUseProxy,
                                                    AzureStackHubProxySettings.ProxyOnlyAzureStackHub]:
            # If we should not use proxy or should use proxy only for the base url and not auth url,
            # then set the alternative proxies to None
            self._auth_alternative_proxies = {}

        if self._azure_stack_hub_proxy_settings in [AzureStackHubProxySettings.DoNotUseProxy,
                                                    AzureStackHubProxySettings.ProxyOnlyAuth]:
            # If we should not use proxy or should use proxy only for the base url and not auth url,
            # then set the alternative proxies to None
            self._mgmt_url_alternative_proxies = {}

        super().__init__(self._management_url,
                         headers={
                             'Content-Type': 'application/json',
                             'Accept': 'application/json'
                         },
                         **kwargs)

        # Initialize all clients
        self.compute = AzureComputeConnection(self)

    def _mgmt_refresh_token(self):
        last_refresh = self._mgmt_token_last_refresh
        expires_in = self._mgmt_token_expires_in

        if last_refresh and expires_in \
                and last_refresh + datetime.timedelta(seconds=expires_in) > datetime.datetime.now():
            return

        body_params = f'grant_type=client_credentials' \
            f'&client_id={self._app_client_id}' \
            f'&client_secret={self._app_client_secret}' \
            f'&resource={self._resource}'

        response = self._post(f'{self._auth_url}/{self.tenant_id}/oauth2/token',
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                              body_params=body_params,
                              force_full_url=True,
                              use_json_in_body=False,
                              alternative_proxies=self._auth_alternative_proxies
                              )
        if 'access_token' not in response:
            raise RESTException(f'Invalid Response: {response}')
        self._mgmt_token = response['access_token']
        self._mgmt_token_last_refresh = datetime.datetime.now()
        self._mgmt_token_expires_in = int(response['expires_in']) - 600     # be on the safe side with 10 minutes

    # Resource Management API (https://docs.microsoft.com/en-us/rest/api/azure/)
    def _rm_request(self, *args, **kwargs):
        self._mgmt_refresh_token()

        kwargs['alternative_proxies'] = self._mgmt_url_alternative_proxies

        api_version = kwargs.pop('api_version', None)
        if not api_version:
            api_version = DEFAULT_API_VERSION

        if not kwargs.get('url_params'):
            kwargs['url_params'] = {'api-version': api_version}
        elif not kwargs.get('url_params', {}).get('api-version'):
            kwargs['url_params']['api-version'] = api_version

        response = self._do_request(
            *args,
            extra_headers={'Authorization': f'Bearer {self._mgmt_token}'},
            raise_for_status=False,
            use_json_in_response=False,
            return_response_raw=True,
            **kwargs
        )

        if response.status_code == 429:
            self.handle_sync_429_default(response)
            return self._graph_request(*args, **kwargs)

        return self._handle_response(
            response, raise_for_status=True, use_json_in_response=True, return_response_raw=False
        )

    def rm_paginated_request(self, method: str, url: str, **kwargs):
        page = 0
        force_full_url = False
        while page < PAGINATION_LIMIT:
            try:
                result = self._rm_request(method, url, force_full_url=force_full_url, **kwargs)
                yield from (result.get('value') or [])
                url = result.get('nextLink')
                if not url:
                    break
                force_full_url = True
                page += 1
            except Exception:
                logger.exception(f'Failed fetching page {page} with url {url}')
                raise

    def rm_paginated_get(self, url: str, api_version=None, **kwargs):
        yield from self.rm_paginated_request('GET', url, api_version=api_version, **kwargs)

    # Graph API (https://docs.microsoft.com/en-us/graph/api/overview?toc=.%2Fref%2Ftoc.json&view=graph-rest-1.0)
    def _graph_refresh_token(self):
        last_refresh = self._graph_token_last_refresh
        expires_in = self._graph_token_expires_in

        if last_refresh and expires_in \
                and last_refresh + datetime.timedelta(seconds=expires_in) > datetime.datetime.now():
            return

        context = adal.AuthenticationContext(
            f'{self._auth_url}/{self.tenant_id}', proxies=self._proxies, verify_ssl=self._verify_ssl)

        response = context.acquire_token_with_client_credentials(
            self._graph_url,
            self._app_client_id,
            self._app_client_secret)

        if 'accessToken' not in response:
            logger.error(f'Error authenticating, response is {response}')
            raise RESTException(f'Auth error')

        self._graph_token = response['accessToken']
        self._graph_token_last_refresh = datetime.datetime.now()
        self._graph_token_expires_in = int(response.get('expiresIn') or 60 * 20) - 600

    def _graph_request(self, *args, **kwargs):
        self._graph_refresh_token()

        response = self._do_request(
            *args,
            extra_headers={'Authorization': f'Bearer {self._graph_token}'},
            raise_for_status=False,
            use_json_in_response=False,
            return_response_raw=True,
            **kwargs
        )

        if response.status_code == 429:
            self.handle_sync_429_default(response)
            return self._graph_request(*args, **kwargs)

        return self._handle_response(
            response, raise_for_status=True, use_json_in_response=True, return_response_raw=False
        )

    def graph_paginated_request(self, method, resource, version):
        # Take care of paging generically: https://developer.microsoft.com/en-us/graph/docs/concepts/paging
        version = version or 'v1.0'
        url = f'{self._graph_url.rstrip("/")}/{version.strip("/")}/{resource.strip("/")}'

        result = self._graph_request(method, url)
        yield from result['value']

        page_num = 1
        while '@odata.nextLink' in result and page_num < PAGINATION_LIMIT:
            result = self._get(result['@odata.nextLink'], force_full_url=True)
            yield from result['value']
            page_num += 1

    def graph_paginated_get(self, resource, version=None):
        yield from self.graph_paginated_request('GET', resource, version)

    # Generic
    def _connect(self):
        if not self._app_client_id or not self._app_client_secret or not self.tenant_id:
            raise RESTException('No Client ID or Secret or Tenant ID')

        self._mgmt_token_last_refresh = None
        self._mgmt_token_expires_in = None
        self._graph_token_last_refresh = None
        self._graph_token_expires_in = None

        self._mgmt_refresh_token()
        self._graph_refresh_token()

    def get_device_list(self):
        raise NotImplementedError()

    def get_tenants_list(self):
        yield from self.rm_paginated_get('tenants', api_version='2020-01-01')
