from enum import Enum

DEVICES_PER_PAGE_PERCENTAGE = 10
DEVICES_PER_PAGE = 100
MAX_DEVICES_PER_PAGE = 500  # Max 5000
MAX_NUMBER_OF_DEVICES = 200000
REQUEST_RETRIES = 10
RETRIES_SLEEP_TIME = 5
REFRESH_TOKEN_REQUESTS = 400

MAX_POLICIES_LENGTH = 1000


class PolicyTypes(Enum):
    Prevention = 'prevention'
    SensorUpdate = 'sensor_update'

    def replace_to_dash(self):
        return self.value.replace('_', '-')
