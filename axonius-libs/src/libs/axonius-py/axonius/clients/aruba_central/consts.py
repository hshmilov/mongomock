DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 20000000

SEC_IN_DAY = 86400
DEFAULT_TOKEN_EXPIRE_TIME_SEC = 7200  # 2 Hours

API_URL_LOGIN_SUFFIX = 'oauth2/authorize/central/api/login'
API_URL_AUTHENTICATION_SUFFIX = 'oauth2/authorize/central/api'
API_URL_TOKEN_SUFFIX = 'oauth2/token'

API_URL_ACCESS_POINT_SUFFIX = 'monitoring/v1/aps'
API_URL_SWITCH_SUFFIX = 'monitoring/v1/switches'

ACCESS_POINT_TYPE = 'Access Point'
ACCESS_POINT_API_FIELD = 'aps'
SWITCH_TYPE = 'Switch'
SWITCH_API_FIELD = 'switches'

REGIONS = {
    'US-1': 'app1-apigw.central.arubanetworks.com',
    'US-2': 'apigw-prod2.central.arubanetworks.com',
    'EU-1': 'eu-apigw.central.arubanetworks.com',
    'Canada-1': 'apigw-ca.central.arubanetworks.com',
    'China-1': 'apigw.central.arubanetworks.com.cn',
    'APAC-1': 'api-ap.central.arubanetworks.com',
    'APAC-EAST1': 'apigw-apaceast.central.arubanetworks.com',
    'APAC-SOUTH1': 'apigw-apacsouth.central.arubanetworks.com'
}
