import logging

from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from azure_adapter.consts import SUBSCRIPTION_API_VERSION, AZURE_CHINA_LOGIN_URL, \
    AZURE_CHINA_MGMT_URL, AZURE_USGOV_LOGIN_URL, AZURE_USGOV_MGMT_URL, \
    AZURE_DEGOV_LOGIN_URL, AZURE_DEGOV_MGMT_URL, AZURE_DEFAULT_LOGIN_URL, \
    AZURE_DEFAULT_MGMT_URL

logger = logging.getLogger(f'axonius.{__name__}')


class SubscriptionConnection(RESTConnection):
    """ REST client to pull Azure Subscriptions. """
    DEFAULT_CLOUD = 'Azure Public Cloud'

    def __init__(self, *args,
                 client_id: str,
                 client_secret: str,
                 directory_id: str,
                 cloud_name: str = None,
                 **kwargs):
        super().__init__(*args,
                         url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._client_id = client_id
        self._client_secret = client_secret
        self._directory_id = directory_id
        self._resource = AZURE_DEFAULT_MGMT_URL
        self._apikey = ''
        self.subscriptions = []

        self._cloud_name = cloud_name or self.DEFAULT_CLOUD

        self._base_auth_url = self._set_cloud_url(cloud_name, service='auth')
        self._base_mgmt_url = self._set_cloud_url(cloud_name, service='mgmt')

    @staticmethod
    def _set_cloud_url(cloud_name: str, service: str):
        if cloud_name == 'AzureChinaCloud':
            if service == 'auth':
                url = AZURE_CHINA_LOGIN_URL
            else:
                url = AZURE_CHINA_MGMT_URL
        elif cloud_name == 'AzureUSGovernment':
            if service == 'auth':
                url = AZURE_USGOV_LOGIN_URL
            else:
                url = AZURE_USGOV_MGMT_URL
        elif cloud_name == 'AzureGermanCloud':
            if service == 'auth':
                url = AZURE_DEGOV_LOGIN_URL
            else:
                url = AZURE_DEGOV_MGMT_URL
        else:
            if service == 'auth':
                url = AZURE_DEFAULT_LOGIN_URL
            else:
                url = AZURE_DEFAULT_MGMT_URL
        return url

    def _create_apikey(self):
        """ Call the Microsoft login service to retrieve a Bearer token
        and populate the apikey.
        """
        # this is a different domain than self._domain
        token_url = f'{self._base_auth_url}' \
                    f'/{self._directory_id}/oauth2/token'

        body_params = f'grant_type=client_credentials' \
                      f'&client_id={self._client_id}' \
                      f'&client_secret={self._client_secret}' \
                      f'&resource={self._resource}'

        try:
            response = self._post(name=token_url,
                                  extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                  body_params=body_params,
                                  force_full_url=True,
                                  use_json_in_body=False,
                                  )
            return response.get('access_token') or None
        except Exception as err:
            logger.exception(f'Connection to the login service failed: str({err})')
            return None

    # pylint: disable=protected-access
    def populate_subscriptions(self):
        subs_url = f'{self._base_mgmt_url}/subscriptions?api-version=' \
                   f'{SUBSCRIPTION_API_VERSION}'

        try:
            response = self._get(subs_url, force_full_url=True)
            subscriptions_raw = response.get('value')

            if isinstance(subscriptions_raw, list):
                self.subscriptions.extend(self._parse_subscriptions(subscriptions_raw))
        except Exception as err:
            logger.exception(f'Unable to retrieve subscriptions: str({err})')

        if not self.subscriptions:
            message = f'No Azure Subscriptions found. Please check "Fetch All ' \
                      f'Subscriptions", provide a Subscription ID in the ' \
                      f'adapter settings or verify that you have sufficient ' \
                      f'privileges.'
            logger.warning(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _parse_subscriptions(subscriptions_raw) -> list:
        return [subscription.get('subscriptionId') for subscription in
                subscriptions_raw if subscription.get('subscriptionId')]

    def _connect(self):
        """ Connect to Azure and fetch all available subscriptions. """
        if not self._apikey:
            self._apikey = self._create_apikey()

        self._session_headers['Authorization'] = f'Bearer {self._apikey}'
        subs_url = f'{self._base_mgmt_url}/subscriptions?api-version=' \
                   f'{SUBSCRIPTION_API_VERSION}'
        try:
            response = self._get(subs_url, force_full_url=True)
        except Exception as err:
            logger.exception(f'Unable to connect to the Azure service:'
                             f' str({err})')
            raise

    def get_device_list(self):
        pass
