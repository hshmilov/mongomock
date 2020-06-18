import logging
from datetime import datetime, timedelta
from typing import Dict, List

import adal

from axonius.clients.rest.connection import (ASYNC_ERROR_SLEEP_TIME,
                                             ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE,
                                             MAX_ASYNC_RETRIES, RESTConnection)
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


AUTHORITY_HOST_URL = 'https://login.microsoftonline.com'
CHINA_AUTHORITY_HOST_URL = 'https://login.partner.microsoftonline.cn'
GRAPH_API_URL = 'https://graph.microsoft.com'
GRAPH_API_PREFIX_BETA = '/beta'
GRAPH_API_PREFIX_BASE = '/v1.0'
CHINA_GRAPH_API_URL = 'https://microsoftgraph.chinacloudapi.cn'
AZURE_AD_GRAPH_API_URL = 'https://graph.windows.net'    # legacy api required for azure ad b2c
CHINA_AZURE_AD_GRAPH_API_URL = 'https://graph.chinacloudapi.cn'
TEMPLATE_AUTHZ_URL = 'https://login.windows.net/{tenant_id}/oauth2/authorize?response_type=code&client_id={client_id}' \
                     '&redirect_uri=https://localhost&state=after-auth&resource=https://graph.microsoft.com' \
                     '&prompt=admin_consent'
DEFAULT_EXPIRATION_IN_SECONDS = 60 * 20     # 20 min
MAX_PAGE_NUM_TO_AVOID_INFINITE_LOOP = 20000
LOG_DEVICES_COUNT = 50
USERS_ATTRIBUTES = [
    'accountEnabled',
    'city',
    'country',
    'department',
    'displayName',
    'givenName',
    'surname',
    'id',
    'jobTitle',
    'mail',
    'mobilePhone',
    'onPremisesDomainName',
    'onPremisesSamAccountName',
    'onPremisesSecurityIdentifier',
    'onPremisesUserPrincipalName',
    'onPremisesSyncEnabled',
    'onPremisesImmutableId',
    'onPremisesLastSyncDateTime',
    'streetAddress',
    'passwordPolicies',
    'userPrincipalName',
    'userType'
    'createdDateTime',
    'isResourceAccount',
    'lastPasswordChangeDateTime',
    'employeeId',
]

USERS_ATTRIBUTES_BETA = [
    'signInActivity',
]  # Unused because of bug in MS Graph API BETA as of 4 Jun 2020

DEVICE_ATTRIBUTES = [
    'accountEnabled',
    'approximateLastSignInDateTime',
    'deviceId',
    'displayName',
    'id',
    'isCompliant',
    'isManaged',
    'onPremisesLastSyncDateTime',
    'onPremisesSyncEnabled',
    'operatingSystem',
    'operatingSystemVersion',
    'trustType'
]


# pylint: disable=logging-format-interpolation, too-many-instance-attributes
class AzureAdClient(RESTConnection):
    def __init__(self,
                 client_id,
                 client_secret,
                 tenant_id,
                 *args,
                 is_azure_ad_b2c=None,
                 azure_region=None,
                 allow_beta_api=False,
                 allow_fetch_mfa=False,
                 parallel_count=ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE,
                 async_retry_time=ASYNC_ERROR_SLEEP_TIME,
                 async_retry_max=MAX_ASYNC_RETRIES,
                 **kwargs):
        self._parallel_count = parallel_count
        self._async_retry_time = async_retry_time
        self._async_retry_max = async_retry_max
        self._allow_beta_api = allow_beta_api
        self._allow_fetch_mfa = allow_fetch_mfa
        self._client_id = client_id
        self._client_secret = client_secret
        self._tenant_id = tenant_id
        self._refresh_token = None
        self._is_azure_ad_b2c = is_azure_ad_b2c

        logger.info(f'Creating Azure AD with tenant {tenant_id} and client id {client_id}. '
                    f'B2C: {bool(is_azure_ad_b2c)} azure_region: {azure_region}')
        if is_azure_ad_b2c:
            if str(azure_region).lower() == 'china':
                self._api_endpoint = CHINA_AZURE_AD_GRAPH_API_URL
                self._authority_host_url = CHINA_AUTHORITY_HOST_URL
            else:
                self._api_endpoint = AZURE_AD_GRAPH_API_URL
                self._authority_host_url = AUTHORITY_HOST_URL
            url_base_prefix = f'/{self._tenant_id}'
        else:
            if str(azure_region).lower() == 'china':
                self._api_endpoint = CHINA_GRAPH_API_URL
                self._authority_host_url = CHINA_AUTHORITY_HOST_URL
            else:
                self._api_endpoint = GRAPH_API_URL
                self._authority_host_url = AUTHORITY_HOST_URL
            url_base_prefix = GRAPH_API_PREFIX_BETA if allow_beta_api else GRAPH_API_PREFIX_BASE
        super().__init__(domain=self._api_endpoint, url_base_prefix=url_base_prefix, *args, **kwargs)

    def set_refresh_token(self, refresh_token):
        self._refresh_token = refresh_token

    def get_refresh_token_from_authorization_code(self, authorization_code):
        context = adal.AuthenticationContext(f'{self._authority_host_url}/{self._tenant_id}',
                                             proxies=self._proxies, verify_ssl=self._verify_ssl)
        answer = context.acquire_token_with_authorization_code(
            authorization_code,
            'https://localhost',
            self._api_endpoint,
            self._client_id,
            self._client_secret
        )

        if 'refreshToken' not in answer:
            raise ValueError(f'Authentication error: {answer}')

        return answer['refreshToken']

    def _connect(self):
        try:
            context = adal.AuthenticationContext(f'{self._authority_host_url}/{self._tenant_id}',
                                                 proxies=self._proxies, verify_ssl=self._verify_ssl)
            if self._refresh_token:
                token_answer = context.acquire_token_with_refresh_token(
                    self._refresh_token,
                    self._client_id,
                    self._api_endpoint,
                    self._client_secret
                )
            else:
                token_answer = context.acquire_token_with_client_credentials(
                    self._api_endpoint,
                    self._client_id,
                    self._client_secret)
                logger.info('Authorization URL for oauth: {0}'.format(
                    TEMPLATE_AUTHZ_URL.format(tenant_id=self._tenant_id, client_id=self._client_id)
                ))

            if 'accessToken' not in token_answer:
                logger.error(f'Error authenticating, response is {token_answer}')
                raise RESTException(f'Auth error')

            # This token has expiration date
            self._access_token = token_answer['accessToken']
            self._access_token_expires_in = int(token_answer.get('expiresIn') or DEFAULT_EXPIRATION_IN_SECONDS)
            self._token_expires_date = datetime.now() + timedelta(seconds=self._access_token_expires_in)

            self._session_headers = {'Authorization': f'Bearer {self._access_token}'}
        except adal.adal_error.AdalError as e:
            logger.exception(f'Error getting token')

            if 'error validating credentials' in str(e).lower():
                raise RESTException(f'Error validating credentials')
            if 'was not found in the directory' in str(e).lower():
                raise RESTException(f'Application ID was not found in the directory')
            if 'not found. this may happen if there are no active subscriptions for the tenant.' in str(e).lower():
                raise RESTException(f'Tenant ID {self._tenant_id} not found')
            raise

    def _renew_token_if_needed(self):
        if datetime.now() >= self._token_expires_date:
            self._connect()

    def _get(self, *args, **kwargs):
        self._renew_token_if_needed()
        return super()._get(*args, **kwargs)

    # pylint: disable=arguments-differ
    def _async_get(self, *args, **kwargs):
        self._renew_token_if_needed()
        return super()._async_get(*args,
                                  chunks=self._parallel_count,
                                  max_retries=self._async_retry_max,
                                  retry_sleep_time=self._async_retry_time,
                                  **kwargs)

    def _paged_get(self, resource):
        # Take care of paging generically: https://developer.microsoft.com/en-us/graph/docs/concepts/paging
        result = self._get(resource)
        yield from result['value']

        page_num = 1
        while '@odata.nextLink' in result and page_num < MAX_PAGE_NUM_TO_AVOID_INFINITE_LOOP:
            result = self._get(result['@odata.nextLink'], force_full_url=True)
            yield from result['value']
            page_num += 1

    def get_installed_apps(self) -> Dict[str, List[Dict]]:
        """
        Get installed apps on azure Intune.
        first request is for deviceManagement/detectedApps for getting app data
        the next request is for deviceManagement/detectedApps/{app_id}/managedDevices
        for getting devices that have this app installed on them.
        so the best thing to do is save a dict containing devices ids and their installed apps.
        :return:dict of devices and their apps, for example: devices_apps[DEVICE_ID] = [{app_data}, ..]
        """
        devices_apps = {}
        try:
            logger.info('Getting Installed Apps')
            apps_got = 0
            for app_raw in self._paged_get('deviceManagement/detectedApps'):
                app_id = app_raw.get('id')
                if not app_id:
                    continue
                for device_raw in self._paged_get(f'deviceManagement/detectedApps/{app_id}/managedDevices'):
                    device_id = device_raw.get('id')
                    if not device_id:
                        continue
                    devices_apps.setdefault(device_id, []).append(app_raw)
                apps_got += 1
                if apps_got % LOG_DEVICES_COUNT == 0:
                    logger.info(f'Got {apps_got} installed apps')
        except Exception:
            logger.exception('Cant get Intune installed apps')
        return devices_apps

    def get_device_list(self):
        if self._is_azure_ad_b2c:
            logger.info(f'Azure AD B2C: Not yielding deviecs')
            return
        for device_raw in self._paged_get(f'devices?$select={",".join(DEVICE_ATTRIBUTES)}'):
            yield device_raw, 'Azure AD'
        try:
            devices_apps = self.get_installed_apps()
            for device_raw in self._paged_get(f'deviceManagement/managedDevices'):
                dev_id = device_raw.get('id')
                installed_apps = devices_apps.get(dev_id) if devices_apps.get(dev_id) else []
                device_raw['installed_apps'] = installed_apps
                yield device_raw, 'Intune'
        except Exception:
            logger.exception(f'Cant get Intune')

    def get_user_list(self):
        if self._is_azure_ad_b2c:
            yield from self._paged_get(f'users?api-version=1.6')
        else:
            yield from self._get_graph_user_list()

    @staticmethod
    def _extract_user_pn_and_endpoint(request_dict):
        request = request_dict.get('name')
        if not (request and isinstance(request, str)):
            return None
        if request.startswith('user'):
            return request.split('/')[1], 'memberOf'
        if request.startswith('reports'):
            fltr_str = request_dict.get('url_params').get('$filter')
            return fltr_str.partition('eq')[-1].strip().replace('\'', ''), 'credsDetails'
        return None

    # pylint: disable=too-many-branches
    def _get_graph_user_list(self):
        user_by_user_pn = dict()  # dict of userPrincipalName to user object
        async_requests_chunks = list()  # list of chunks of requests to perform asynchronously
        requests_chunk = list()  # list of requests, aka chunk
        internal_chunk_size = min(self._parallel_count * 5, 50)  # To improve async performance
        # Get all users immediately because paging in Graph API is unpredictable
        for idx, user in enumerate(self._iter_graph_users()):
            # check that user has a principal name
            try:
                user_pn = user.get('userPrincipalName')
                if not (user_pn and isinstance(user_pn, str)):
                    logger.error(f'Failed to get userPrincipalName for user {user}')
                    continue
            except Exception:
                logger.exception(f'Failed to get userPrincipalName for user {user}')
                continue
            # Check if the user pn is already known, so we don't
            # schedule extra fetches for that pn...
            if user_pn in user_by_user_pn:
                logger.warning(f'User PN {user_pn} already known, skipping...')
                continue

            # add resulting object to dict
            user_by_user_pn.setdefault(user_pn, user)

            # add memberOf() request for the user
            if '#EXT#' not in user_pn:
                # Skip #EXT# users!!!
                requests_chunk.append({
                    'name': f'users/{user_pn}/memberOf',
                    'url_params': {'$select': 'displayName'}
                })
                # handle mfa
                if self._allow_fetch_mfa:
                    # READ ME!
                    # using beta api to fetch! Will fail if beta api not allowed
                    # Unless this functionality is added to GA. So we do not check if it's enabled,
                    # for future-proofing.
                    # requires Reports.Read.All permission
                    requests_chunk.append({
                        'name': 'reports/credentialUserRegistrationDetails',
                        'url_params': {'$filter': f'userPrincipalName eq \'{user_pn}\''}
                    })
            # add this chunk to queue if the chunk is full
            if idx and idx % internal_chunk_size == 0:
                logger.info(f'Chunk has {len(requests_chunk)} requests. Flushing...')
                async_requests_chunks.append(requests_chunk)
                logger.info(f'Flushing chunk: {idx}, total chunks: {len(async_requests_chunks)}')
                requests_chunk = list()
        # add last chunk if needed
        if requests_chunk:
            async_requests_chunks.append(requests_chunk)
        # iterate over chunks, perform each chunk asynchronously
        for idx, async_requests in enumerate(async_requests_chunks):
            logger.info(f'Dealing with chunk {idx} of {len(async_requests_chunks)}')
            # All that was done so that the token can be refreshed between chunks
            # async_get refreshes token
            # now run through the responses, match each response to a user
            for request_dict, response in zip(async_requests, self._async_get(async_requests, retry_on_error=True)):
                if not self._is_async_response_good(response):
                    logger.debug(f'Bad async response for {request_dict}, got: {response} ')
                    continue
                try:
                    user_pn, endpoint = self._extract_user_pn_and_endpoint(request_dict)
                    user = user_by_user_pn[user_pn]
                    user[endpoint] = response['value']
                except Exception:
                    logger.exception(f'Failed to parse response for request {request_dict}')
                    continue

        yield from user_by_user_pn.values()

    def _iter_graph_users(self):
        attrs = USERS_ATTRIBUTES
        # if self._allow_beta_api:
        #     attrs = USERS_ATTRIBUTES + USERS_ATTRIBUTES_BETA
        # These two lines commented out due to bug in MS Graph API BETA, as of 4 JUN 2020
        # We have to specify the attributes, "*" is not supported.
        yield from self._paged_get(f'users?$select={",".join(attrs)}')

    def test_connection(self):
        self.connect()
        try:
            if self._is_azure_ad_b2c:
                for _ in self._paged_get(f'users?api-version=1.6'):
                    break
            else:
                self._get(f'users?$top=1')
        except Exception as e:
            if 'insufficient privileges to complete the operation' in str(e).lower():
                raise RESTException(f'Insufficient permissions. Did you grant this application '
                                    f'Graph API readonly permissions?')
            raise
