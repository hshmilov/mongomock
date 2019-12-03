from collections import namedtuple
from enum import Enum, auto

ISE_ERS_PORT = 9060
ERS_URL_BASE_PREFIX = '/ers'

ISE_PXGRID_PORT = 8910
PXGRID_URL_BASE_PREFIX = '/pxgrid'

REQUIRED_SCHEMA_FIELDS = (
    'domain',
    'username',
    'password',
    'pxgrid',
    'verify_ssl',
)

SCHEMA_FIELDS = ('https_proxy', ) + REQUIRED_SCHEMA_FIELDS


ClientConfig = namedtuple('ClientConfig', SCHEMA_FIELDS)
CLIENT_CONFIG_FIELDS = ClientConfig(*SCHEMA_FIELDS)

CLIENT_CONFIG_TITLES = ClientConfig(domain='Cisco ISE Domain',
                                    username='User Name',
                                    password='Password',
                                    pxgrid='Use pxGrid to fetch live sessions',
                                    verify_ssl='Verify SSL',
                                    https_proxy='HTTPS Proxy')

PxGridObject = namedtuple('PxGrid', ('client_id', 'username', 'password'))

FETCH_ENDPOINTS_FIELD = 'fetch_endpoints'
FETCH_ENDPOINTS_TITLE = 'Fetch Endpoints'

SECRETS = ['previousSharedSecret', 'roCommunity', 'radiusSharedSecret', 'sharedSecret']


MAX_NETWORK_DEVICE_PAGE = 1000
PAGE_SIZE = 100


class CiscoIseDeviceType(Enum):
    NetworkDevice = auto()
    EndpointDevice = auto()
    LiveSessionDevice = auto()
