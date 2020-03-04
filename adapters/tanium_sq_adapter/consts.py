DEVICE_PER_PAGE = 200
MAX_DEVICES_COUNT = 2000000

STRONG_SENSORS = [
    'Computer Name',
    'Network Adapters',
    'Computer Serial Number',
]
PAGE_SIZE = 1000
SLEEP_POLL_ANSWERS = 15
SLEEP_GET_ANSWERS = 2
SLEEP_REASK = 15
RETRIES_REASK = 5
CACHE_EXPIRATION = 900
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/plain, */*',
    'User-Agent': 'axonius/tanium_sq_adapter',
}
