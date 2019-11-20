import logging
from datetime import datetime, timedelta
from typing import Dict, List

import adal
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


AUTHORITY_HOST_URL = 'https://login.microsoftonline.com'
GRAPH_API_URL = 'https://graph.microsoft.com'
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


# pylint: disable=logging-format-interpolation
class AzureAdClient(RESTConnection):
    def __init__(self, client_id, client_secret, tenant_id, *args, **kwargs):
        self._client_id = client_id
        self._client_secret = client_secret
        self._tenant_id = tenant_id
        self._refresh_token = None
        super().__init__(domain=GRAPH_API_URL, url_base_prefix='/v1.0', *args, **kwargs)

    def set_refresh_token(self, refresh_token):
        self._refresh_token = refresh_token

    def get_refresh_token_from_authorization_code(self, authorization_code):
        context = adal.AuthenticationContext(f'{AUTHORITY_HOST_URL}/{self._tenant_id}',
                                             proxies=self._proxies, verify_ssl=self._verify_ssl)
        answer = context.acquire_token_with_authorization_code(
            authorization_code,
            'https://localhost',
            GRAPH_API_URL,
            self._client_id,
            self._client_secret
        )

        if 'refreshToken' not in answer:
            raise ValueError(f'Authentication error: {answer}')

        return answer['refreshToken']

    def _connect(self):
        try:
            context = adal.AuthenticationContext(f'{AUTHORITY_HOST_URL}/{self._tenant_id}',
                                                 proxies=self._proxies, verify_ssl=self._verify_ssl)
            if self._refresh_token:
                token_answer = context.acquire_token_with_refresh_token(
                    self._refresh_token,
                    self._client_id,
                    GRAPH_API_URL,
                    self._client_secret
                )
            else:
                token_answer = context.acquire_token_with_client_credentials(
                    GRAPH_API_URL,
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
