from enum import Enum

DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000
FILTER_DATE_FORMAT = '%Y-%m-%dT%Hh%M'


class GvmProtocols(Enum):
    SSH = 22
    TLS = 9390
