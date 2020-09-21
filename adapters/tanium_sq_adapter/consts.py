# DEVICE_PER_PAGE = 200
MAX_DEVICES_COUNT = 2000000
IPV4_SENSOR = 'IPv4 Address'
MAC_SENSOR = 'MAC Address'
CID_SENSOR = 'Computer ID'
CNAME_SENSOR = 'Computer Name'
CSN_SENSOR = 'Computer Serial Number'
NET_SENSORS = [IPV4_SENSOR, MAC_SENSOR]
NET_SENSOR_DISCOVER = 'Network Adapters'

REQUIRED_SENSORS = [CID_SENSOR, CNAME_SENSOR, CSN_SENSOR]

# SLEEP_REASK = 15
# RETRIES_REASK = 5

PAGE_SIZE = 1000
SLEEP_POLL_ANSWERS = 15
SLEEP_GET_ANSWERS = 2
REASK_SLEEP = 5
REASK_RETRIES = 5
CACHE_EXPIRATION = 900
MAX_HOURS = 24
NO_RESULTS_WAIT = False
REFRESH = False

HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/plain, */*',
    'User-Agent': 'axonius/tanium_sq_adapter',
}
