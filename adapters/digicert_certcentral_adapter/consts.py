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
