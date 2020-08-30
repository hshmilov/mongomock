from enum import Enum


class AuthenticationMethods(Enum):
    Cyberark = 'CyberArk'
    Windows = 'Windows'
    LDAP = 'LDAP'
    Radius = 'RADIUS'


MAX_NUMBER_OF_USERS = 2000000

API_LOGON_SUFFIX = 'PasswordVault/API/auth/{}/Logon'
USERS_API_SUFFIX = 'PasswordVault/api/Users'
USER_LEGACY_API = 'PasswordVault/WebServices/PIMServices.svc/Users'

EXTRA_LEGACY = 'extra_legacy'
