import os
from pathlib import Path

from axonius.consts.plugin_consts import AXONIUS_SETTINGS_DIR_NAME

INCORRECT_PASSWORD = 'Incorrect!'
UNMATCHED_PASSWORD1 = 'Unmatched!'
UNMATCHED_PASSWORD2 = 'Unmatched!2'
NEW_PASSWORD = 'NewPassword!'
BAD_USERNAME = 'BadUsername'
BAD_PASSWORD = 'BadPassword'
VALID_EMAIL = 'lalala@lalala.com'

ROOT_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..')
LOGGED_IN_MARKER = Path(ROOT_DIR) / AXONIUS_SETTINGS_DIR_NAME / '.logged_in'
GUI_LOG_PATH = os.path.join(ROOT_DIR, 'logs', 'gui', 'gui.axonius.log')

RESTRICTED_USERNAME = 'RestrictedUser'
FIRST_NAME = 'FirstName'
LAST_NAME = 'LastName'
TAG_NAME = 'lalala'

RESTRICTED_ENTITY_USERNAME = 'RestrictedEntityUser'
NOTES_USERNAME = 'NotesUser'

HIDDEN_USER_NEW_PASSWORD = 'test_pass_2'

LOCAL_DEFAULT_USER_PATTERN = 'admin[internal]'
NONE_USER_PATTERN = 'None[None]'

TEMP_FILE_PREFIX = 'temp_file_upload'

NOTE_COLUMN = 'Note'

JSON_ADAPTER_NAME = 'JSON File'
JSON_ADAPTER_SEARCH = 'json'
JSON_ADAPTER_PLUGIN_NAME = 'json_file_adapter'


class EmailSettings:
    port = '25'
    host = 'services.axonius.lan'


class QueriesScreen:
    query_1 = 'adapters == size(1)'
    query_1_name = 'test_saved_query_1'


class Enforcements:
    enforcement_name_1 = 'test_enforcement_1'
    enforcement_query_1 = 'Windows Operating System'


class Saml:
    idp = 'test_idp_1'
    cert = 'certificate'
    cert_content = 'certfilecontent'


class Notes:
    note1_text = 'note1_text'
    note1_device_filter = 'Big-Export'


class History:
    history_depth = 30
    entities_per_day = 4000


class Tags:
    tag_1 = 'tag_1'


class Account:
    file_path = 'account_data.tmp'


class Reports:
    test_report_no_email = 'test_report_no_email'
    test_report_with_email = 'test_report_with_email'
