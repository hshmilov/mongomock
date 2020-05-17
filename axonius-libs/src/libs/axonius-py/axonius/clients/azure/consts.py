from enum import Enum, auto


class AzureClouds(Enum):
    Public = auto()
    Gov = auto()
    China = auto()
    Germany = auto()


class AzureStackHubProxySettings(Enum):
    DoNotUseProxy = 'Do not use proxy'
    ProxyOnlyAuth = 'proxy authentication only'
    ProxyOnlyAzureStackHub = 'Proxy Azure Stack Hub only'
    ProxyAll = 'Proxy all'


AZURE_SUBSCRIPTION_ID = 'subscription_id'
AZURE_CLIENT_ID = 'client_id'
AZURE_CLIENT_SECRET = 'client_secret'
AZURE_TENANT_ID = 'tenant_id'
AZURE_VERIFY_SSL = 'verify_ssl'
AZURE_ACCOUNT_TAG = 'account_tag'
AZURE_IS_AZURE_AD_B2C = 'is_azure_ad_b2c'
AZURE_HTTPS_PROXY = 'https_proxy'
AZURE_AUTHORIZATION_CODE = 'authorization_code'
AZURE_CLOUD_ENVIRONMENT = 'cloud_environment'
AZURE_AD_CLOUD_ENVIRONMENT = 'azure_region'
AZURE_STACK_HUB_URL = 'azure_stack_hub_url'
AZURE_STACK_HUB_RESOURCE = 'azure_stack_hub_resource'
AZURE_STACK_HUB_PROXY_SETTINGS = 'azure_stack_hub_proxy_settings'


PAGINATION_LIMIT = 1000000      # protect from infinite loop
