DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000

TRANSITIONING_ENUM_VALUES = ['yes', 'no', 'error']

# NOTE: API is not documented well on the internet, get a rancher docker running
#       and browse to the endpoints below for specific endpoint data
#       and https://RANCHER_ENDPOINT/v3/schemas for specific structure data.
RANCHER_LOGIN_PROVIDER_LOCAL = 'v3-public/localProviders/local?action=login'
RANCHER_API_NODES = 'v3/nodes'
