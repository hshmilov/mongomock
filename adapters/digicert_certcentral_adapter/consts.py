from enum import Enum

DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 1000000


class DeviceType(Enum):
    SCANNED_ENDPOINT = 'Scanned Endpoint'
    ORDER = 'Order'


DEVICE_TYPES = [dt.value for dt in DeviceType.__members__.values()]

REST_SERVICES_API = r'https://www.digicert.com/services/v2'
REST_ENDPOINT_AUTH = f'authorization'
REST_ENDPOINT_ORDERS = r'order/certificate'
REST_ENDPOINT_ORDERS_PERMISSION = 'view_orders'

REST_DISCOVERY_API = r'https://daas.digicert.com/apicontroller/v1'
REST_ENDPOINT_DISCOVERY_SCANS_FULL_URL = f'{REST_DISCOVERY_API}/reports/viewIpPort'
REST_ENDPOINT_DISCOVERY_SCANS_PERMISSION = 'view_discovery_scan'

REQUIRED_PERMISSIONS = [REST_ENDPOINT_ORDERS_PERMISSION, REST_ENDPOINT_DISCOVERY_SCANS_PERMISSION]

# Enums taken from https://dev.digicert.com/glossary/#order-status
ENUM_CERT_RATING = ['At risk', 'Not secure', 'Secure', 'Very secure']
ENUM_CERT_STATUS = ['VALID', 'REVOKED', 'EXPIRED', 'UNDETERMINED']
ENUM_CERT_VULNS = ['BEAST', 'BREACH', 'CRIME', 'DROWN', 'FREEK', 'Heartbleed', 'LogJam',
                   'POODLE(SSLv3)', 'POODLE(TLS)', 'RC4', 'SWEET32', 'NO_VULNERABILITY_FOUND']
ENUM_ORDER_STATUS = ['pending', 'reissue_pending', 'rejected', 'processing', 'issued',
                     'revoked', 'canceled', 'needs_csr', 'needs_approval', 'expired']
CERT_STATUS_BY_ORDER_STATUS = {
    'issued': 'VALID',
    'revoked': 'REVOKED',
    'expired': 'EXPIRED',
}

# Note: The following prefixes are monitored in Scalyr. DO NOT CHANGE THEM!
ENUM_UNKNOWN_VALUE_LOG_PREFIX = 'DIGICERT_UNKNOWN_ENUM_VALUE:'
ENUM_BLACKLISTED_VALUE_LOG_PREFIX = 'DIGICERT_BLACKLISTED_ENUM_VALUE:'
