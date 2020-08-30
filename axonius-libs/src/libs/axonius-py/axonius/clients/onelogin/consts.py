USER_PER_PAGE = 50  # Can't be more than 50 according to the documentation.
MAX_NUMBER_OF_USERS = 20000000
DEFAULT_EXPIRES_IN = 36000
EXPIRE_EPSILON = 50
AUTHENTICATION_URL = 'auth/oauth2/v2/token'
USERS_URL = 'api/1/users'
APPS_PER_USER = 'api/1/users/{user_id}/apps'
BODY_PARAMS = {'grant_type': 'client_credentials'}
