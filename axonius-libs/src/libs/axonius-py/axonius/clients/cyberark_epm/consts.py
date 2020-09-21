from enum import Enum


class AuthenticationMethods(Enum):
    EPM = 'EPM'
    Windows = 'Windows'


DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 20000000

POLICIES_PER_PAGE = 99

DEFAULT_SESSION_REFRESH_SEC = 1800

EXTRA_SET = 'extra_set'
EXTRA_POLICY = 'extra_policy'

API_URL_BASE_PREFIX = 'EPM/API'
API_URL_AUTH_SUFFIX = 'Auth/{}/Logon'
API_URL_SETS_SUFFIX = 'Sets'
API_URL_COMPUTERS_SUFFIX = 'Computers'
API_URL_POLICIES_SUFFIX = 'Policies'
