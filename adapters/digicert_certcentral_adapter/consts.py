DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 1000000
# Note: The API specifies the default is 1, I assume it is 1-based.
DEFAULT_START_INDEX = 1

PAGINATION_FIELD_OFFSET = 'startIndex'
PAGINATION_FIELD_PAGE_SIZE = 'pageSize'
PAGINATION_FIELD_COUNT_CURRENT = 'currentCount'
PAGINATION_FIELD_COUNT_TOTAL = 'totalCount'

REST_PATH_SERVICES_API = r'https://www.digicert.com/services/v2'
REST_PATH_AUTH = f'{REST_PATH_SERVICES_API}/authorization'

REST_PATH_DISCOVERY_API = r'https://daas.digicert.com/apicontroller/v1'
REST_PATH_LIST_ENDPOINTS = f'{REST_PATH_DISCOVERY_API}/reports/viewIpPort'

ENUM_CERT_RATING = ['At risk', 'Not secure', 'Secure', 'Very secure']
ENUM_CERT_STATUS = ['VALID', 'REVOKED', 'EXPIRED', 'UNDETERMINED']
ENUM_CERT_VULNS = ['BEAST', 'BREACH', 'CRIME', 'DROWN', 'FREEK', 'Heartbleed', 'LogJam',
                   'POODLE(SSLv3)', 'POODLE(TLS)', 'RC4', 'SWEET32', 'NO_VULNERABILITY_FOUND']
# Note: The following prefixes are monitored in Scalyr. DO NOT CHANGE IT!
ENUM_UNKNOWN_VALUE_LOG_PREFIX = 'DIGICERT_UNKNOWN_ENUM_VALUE:'
ENUM_BLACKLISTED_VALUE_LOG_PREFIX = 'DIGICERT_BLACKLISTED_ENUM_VALUE:'
