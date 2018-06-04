from enum import Enum, auto


class SSLState(Enum):
    Unencrypted = auto()
    Verified = auto()
    Unverified = auto()
