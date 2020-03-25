DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000

# See: https://docs.ipfabric.io/api/#header-token-authentication
INTERVAL_ACCESS_TOKEN_MIN = 30
INTERVAL_REFRESH_TOKEN_HRS = 24

DEVICE_INVENTORY_COLUMNS = ['id', 'configReg', 'devType', 'family', 'hostname', 'image', 'taskKey', 'loginIp',
                            'loginType', 'mac', 'memoryTotalBytes', 'memoryUsedBytes', 'memoryUtilization', 'platform',
                            'processor', 'rd', 'reload', 'siteKey', 'siteName', 'sn', 'stpDomain', 'uptime', 'vendor',
                            'version']
