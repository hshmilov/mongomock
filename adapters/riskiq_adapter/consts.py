DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 20000000
INVENTORY_SEARCH_URL = 'globalinventory/search'
RISKIQ_API_URL_DEFAULT = 'https://api.riskiq.net'
RISKIQ_API_URL_BASE_PREFIX = '/v1'
PAGINATION_SCROLL_DEFAULT = '*'

BODY_PARAM_SEARCH = {
    'filters': {
        'name': 'type',
        'operator': 'EQ',
        'value': 'HOST'
    }
}
