from enum import Enum

DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000


class GvmProtocols(Enum):
    SSH = 22
    TLS = 9390
    # DEBUG = None
