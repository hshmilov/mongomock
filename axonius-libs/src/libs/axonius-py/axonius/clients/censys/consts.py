import copy

DEFAULT_DOMAIN = 'censys.io'

DOMAIN = 'domain'
IS_PAID_TIER = 'is_paid_tier'
API_ID = 'api_id'
API_SECRET = 'api_secret'
SEARCH_QUERY = 'search_query'
SEARCH_TYPE = 'search_type'

BASE_SCHEMA = {
    'items': [
        {
            'name': DOMAIN,
            'title': 'Censys Domain',
            'type': 'string',
            'default': 'censys.io'
        },
        {
            'name': IS_PAID_TIER,
            'title': 'Is Paid Tier',
            'type': 'bool'
        },
        {
            'name': API_ID,
            'title': 'API ID',
            'type': 'string'
        },
        {
            'name': API_SECRET,
            'title': 'API Secret',
            'type': 'string',
            'format': 'password'
        },
        {
            'name': 'https_proxy',
            'title': 'HTTPS Proxy',
            'type': 'string'
        }
    ],
    'required': [
        DOMAIN,
        API_ID,
        API_SECRET,
        IS_PAID_TIER
    ],
    'type': 'array'
}

BASE_DEFAULTS_SCHEMA = {IS_PAID_TIER: False,
                        DOMAIN: DEFAULT_DOMAIN}

ACTION_SCHEMA = copy.deepcopy(BASE_SCHEMA)

ADAPTER_SCHEMA = copy.deepcopy(BASE_SCHEMA)

# Setting up defaults for adapter_schema
for current_item in ADAPTER_SCHEMA['items']:
    if current_item['name'] in BASE_DEFAULTS_SCHEMA:
        current_item['default'] = BASE_DEFAULTS_SCHEMA[current_item['name']]

SEARCH_TYPE_ITEM = {'name': SEARCH_TYPE, 'title': 'Search Type', 'type': 'string', 'enum': ['ipv4', 'websites']}
SEARCH_QUERY_ITEM = {'name': SEARCH_QUERY, 'title': 'Search Query', 'type': 'string'}
ADAPTER_SCHEMA['items'].insert(4, SEARCH_TYPE_ITEM)
ADAPTER_SCHEMA['items'].insert(5, SEARCH_QUERY_ITEM)
ADAPTER_SCHEMA['required'].extend([SEARCH_QUERY, SEARCH_TYPE])
