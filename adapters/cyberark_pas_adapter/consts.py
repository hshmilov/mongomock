from enum import Enum


class AuthenticationMethods(Enum):
    Cyberark = 'CyberArk'
    Windows = 'Windows'
    LDAP = 'LDAP'
    Radius = 'RADIUS'


DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000

API_LOGON_SUFFIX = 'PasswordVault/API/auth/{}/Logon'
