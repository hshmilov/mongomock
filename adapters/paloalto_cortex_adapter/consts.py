from enum import Enum

DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 1000000
CLOUD_URL = 'https://cloud.axonius.com'
ACCESS_TOKEN_ENDPOINT = 'cortex/api/get_accesstoken'
MAX_PANCLOUD_POLL_WAIT_TIME = 30 * 1000
STATUS_CODE_RATE_LIMIT_REACHED = 429
DEFAULT_NUMBER_OF_WEEKS_AGO_TO_FETCH = 2
REFRESH_ACCESS_TOKEN_MINUTES = 30


class DeviceType(Enum):
    Traps = 'Traps'
    GlobalProtect = 'Global Protect'
