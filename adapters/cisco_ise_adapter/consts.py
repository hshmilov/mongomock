from collections import namedtuple

ISE_PORT = 9060
URL_BASE_PREFIX = '/ers'

REQUIRED_SCHEMA_FIELDS = (
    'domain',
    'username',
    'password',
    'verify_ssl',
)

SCHEMA_FIELDS = ('https_proxy', ) + REQUIRED_SCHEMA_FIELDS


ClientConfig = namedtuple('ClientConfig', SCHEMA_FIELDS)
CLIENT_CONFIG_FIELDS = ClientConfig(*SCHEMA_FIELDS)

CLIENT_CONFIG_TITLES = ClientConfig(domain='Cisco ISE Domain',
                                    username='User Name',
                                    password='Password',
                                    verify_ssl='Verify SSL',
                                    https_proxy='HTTPS Proxy')
