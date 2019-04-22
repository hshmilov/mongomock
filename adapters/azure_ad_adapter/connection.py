import logging
from datetime import datetime, timedelta

import adal

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


AUTHORITY_HOST_URL = 'https://login.microsoftonline.com'
GRAPH_API_URL = 'https://graph.microsoft.com'
DEFAULT_EXPIRATION_IN_SECONDS = 60 * 20     # 20 min
MAX_PAGE_NUM_TO_AVOID_INFINITE_LOOP = 20000
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
    'userPrincipalName'
]

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


class AzureAdClient(RESTConnection):
    def __init__(self, client_id, client_secret, tenant_id, *args, **kwargs):
        self._client_id = client_id
        self._client_secret = client_secret
        self._tenant_id = tenant_id
        super().__init__(domain=GRAPH_API_URL, url_base_prefix='/v1.0', *args, **kwargs)

    def _connect(self):
        try:
            context = adal.AuthenticationContext(f'{AUTHORITY_HOST_URL}/{self._tenant_id}', proxies=self._proxies)
            token_answer = context.acquire_token_with_client_credentials(
                GRAPH_API_URL,
                self._client_id,
                self._client_secret)

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

    def _paged_get(self, resource):
        # Take care of paging generically: https://developer.microsoft.com/en-us/graph/docs/concepts/paging
        result = self._get(resource)
        yield from result['value']

        page_num = 1
        while '@odata.nextLink' in result and page_num < MAX_PAGE_NUM_TO_AVOID_INFINITE_LOOP:
            result = self._get(result['@odata.nextLink'], force_full_url=True)
            yield from result['value']
            page_num += 1

    def get_device_list(self):
        for device_raw in self._paged_get(f'devices?$select={",".join(DEVICE_ATTRIBUTES)}'):
            yield device_raw, 'Azure AD'
        try:
            for device_raw in self._paged_get(f'deviceManagement/managedDevices'):
                yield device_raw, 'Intune'
        except Exception:
            logger.exception(f'Cant get Intune')

    def get_user_list(self):
        # We have to specify the attibutes, "*" is not supported.
        yield from self._paged_get(f'users?$select={",".join(USERS_ATTRIBUTES)}')

    def test_connection(self):
        self.connect()
        try:
            for _ in self._paged_get(f'devices?$top=1'):
                break
        except Exception as e:
            if 'insufficient privileges to complete the operation' in str(e).lower():
                raise RESTException(f'Insufficient permissions. Did you grant this application '
                                    f'Graph API readonly permissions?')
            raise
