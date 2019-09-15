from collections import namedtuple
from enum import Enum, auto

REQUIRED_SCHEMA_FIELDS = (
    'domain',
    'username',
    'password',
    'verify_ssl',
)

SCHEMA_FIELDS = (
    'site',
    'https_proxy',
) + REQUIRED_SCHEMA_FIELDS


ClientConfig = namedtuple('ClientConfig', SCHEMA_FIELDS)
CLIENT_CONFIG_FIELDS = ClientConfig(*SCHEMA_FIELDS)

CLIENT_CONFIG_TITLES = ClientConfig(domain='UniFi Contoller domain',
                                    username='User Name',
                                    password='Password',
                                    site='Site',
                                    verify_ssl='Verify SSL',
                                    https_proxy='HTTPS Proxy')


class UnifiAdapterDeviceType(Enum):
    network_device = auto()
    client = auto()


# Connection related
URL_BASE_PREFIX = '/api'
LOGIN_URL = 'login'
DEFAULT_SITE = 'default'
