INCORRECT_PASSWORD = 'Incorrect!'
UNMATCHED_PASSWORD1 = 'Unmatched!'
UNMATCHED_PASSWORD2 = 'Unmatched!2'
NEW_PASSWORD = 'NewPassword!'
BAD_USERNAME = 'BadUsername'
BAD_PASSWORD = 'BadPassword'
VALID_EMAIL = 'lalala@lalala.com'

GUI_LOG_PATH = '../logs/gui/gui.axonius.log'

RESTRICTED_USERNAME = 'RestrictedUser'
FIRST_NAME = 'FirstName'
LAST_NAME = 'LastName'
TAG_NAME = 'lalala'

HIDDEN_USER_NEW_PASSWORD = 'test_pass_2'

LOCAL_DEFAULT_USER_PATTERN = 'admin[internal]'
NONE_USER_PATTERN = 'None[None]'


class EmailSettings:
    port = '25'
    host = 'services.axonius.lan'


class FreshServiceSettings:
    domain = 'fs_domain'
    apikey = 'fs_apikey'
    email = 'fs_email'


class QueriesScreen:
    query_1 = 'adapters == size(1)'
    query_1_name = 'test_saved_query_1'


class Alerts:
    alert_name_1 = 'test_alert_1'
    alert_query_1 = 'Windows Operating System'
