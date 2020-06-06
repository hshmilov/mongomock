DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000
MAX_NUMBER_OF_USERS = 1000000

DOMAIN_CONFIG = 'https://ibosscloud.com'

API_TOKEN_URL = 'https://accounts.iboss.com/ibossauth/web/tokens?ignoreAuthModule=true'
API_SETTING_ID_URL = 'https://www.ibosscloud.com/ibcloud/web/users/mySettings'
API_DOMAINS_URL = 'https://cloud.iboss.com/ibcloud/web/cloudNodesLight'
API_CLOUD_NODES_URL = 'https://www.ibosscloud.com/ibcloud/web/cloudNodes'

STATIC_DEVICE = 'Static Device'
DYNAMIC_DEVICE = 'Dynamic Device'
NODE_DEVICE = 'Node Collection Device'

API_LOGIN_IDS_SUFFIX = '/json/login?ignoreAuthModule=true'
API_STATIC_DEVICE_ENDPOINT_SUFFIX = '/json/computers/static'
API_DYNAMIC_DEVICE_ENDPOINT_SUFFIX = '/json/computers/dynamic'
API_DEVICES_ENDPOINTS = [(API_STATIC_DEVICE_ENDPOINT_SUFFIX, STATIC_DEVICE),
                         (API_DYNAMIC_DEVICE_ENDPOINT_SUFFIX, DYNAMIC_DEVICE)]

API_USER_ENDPOINT_SUFFIX = '/json/users'
API_LOCALSUBNETS_SUFFIX = '/json/network/localSubnets'

API_LOGIN_IDS = {
    'x': '',
    'ldapServer': ''
}

API_PAGINATION = {
    'currentRow': 0,
    'groupNumberFilter': -1,
    'maxItems': DEVICE_PER_PAGE
}
