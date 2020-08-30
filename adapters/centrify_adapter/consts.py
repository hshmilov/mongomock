import re

DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 2000000
GRANT_TYPE_CLIENT = 'client_credentials'
GRANT_TYPE_REFRESH = 'refresh_token'
URL_GET_TOKEN = 'oauth2/token'
URL_USERS = 'CDirectoryService/GetUsers'
URL_APPS = 'UPRest/GetResultantAppsForUser'
URL_QUERY = 'Redrock/query'
QUERY_REDROCK_USERS = 'select * from vaultaccount'
REDROCK_MAX_PER_PAGE = 1000
REDROCK_DATE_REGEX = re.compile('(-*\\d+)')  # Compiled here once for optimization
USER_TYPE_CDIRECTORY = 'cdirectory'
USER_TYPE_VAULTACCOUNT = 'vaultaccount'
