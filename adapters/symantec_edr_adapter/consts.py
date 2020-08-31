DEVICE_PER_PAGE = 100   # Default limit of the vendor
MAX_NUMBER_OF_DEVICES = 20000000

TOKEN_GRANT_TYPE = 'client_credentials'
TOKEN_URL = 'atpapi/oauth2/tokens'
DEVICES_URL = 'atpapi/v2/entities/endpoints'
ENTITIES_RELEASE_URL = 'atpapi/v2/entities/next'
RESOURCE_TTL = 120  # Resource will be released once TTL is reached.

QUERY_VERB = 'query'
WHITE_SPACE = ' '

# This will be used to map disposition code to value.
DISPOSITION_MAP = {
    0: 'Good',
    1: 'Unknown',
    2: 'Suspicious',
    3: 'Bad'
}
