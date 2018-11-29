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

RESTRICTED_ENTITY_USERNAME = 'RestrictedEntityUser'
NOTES_USERNAME = 'NotesUser'

HIDDEN_USER_NEW_PASSWORD = 'test_pass_2'

LOCAL_DEFAULT_USER_PATTERN = 'admin[internal]'
NONE_USER_PATTERN = 'None[None]'

TEMP_FILE_NAME = 'temp_file_upload'

NOTE_COLUMN = 'Note'


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


class Saml:
    idp = 'test_idp_1'
    cert = 'certificate'
    cert_content = 'certfilecontent'


class Notes:
    note1_text = 'note1_text'
    note1_device_filter = 'DESKTOP-MPP10U1'


class History:
    history_depth = 30
    entities_per_day = 4000
    file_path = 'history_upgrade_test.tmp'
