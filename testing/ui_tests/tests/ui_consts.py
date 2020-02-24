import os
from pathlib import Path

from axonius.consts.plugin_consts import AXONIUS_SETTINGS_DIR_NAME
from axonius.consts.system_consts import LOGS_PATH_HOST, CORTEX_PATH

INCORRECT_PASSWORD = 'Incorrect!'
UNMATCHED_PASSWORD1 = 'Unmatched!'
UNMATCHED_PASSWORD2 = 'Unmatched!2'
NEW_PASSWORD = 'NewPassword!'
UPDATE_PASSWORD = 'UpdatePassword!'
BAD_USERNAME = 'BadUsername'
BAD_PASSWORD = 'BadPassword'
VALID_EMAIL = 'lalala@lalala.com'

ROOT_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..')
LOGGED_IN_MARKER = Path(ROOT_DIR) / AXONIUS_SETTINGS_DIR_NAME / '.logged_in'
GUI_LOG_PATH = os.path.join(LOGS_PATH_HOST, 'gui', 'gui.axonius.log')
REPORTS_LOG_PATH = os.path.join(LOGS_PATH_HOST, 'reports', 'reports.axonius.log')
LOGS_AFTER_UPGRADE_PATH = os.path.join(CORTEX_PATH, 'install_dir', 'cortex', 'logs')

RESTRICTED_USERNAME = 'RestrictedUser'
UPDATE_USERNAME = 'UpdateUser'
READ_ONLY_USERNAME = 'ReadOnlyUser'
READ_WRITE_USERNAME = 'ReadWriteUser'
FIRST_NAME = 'FirstName'
UPDATE_FIRST_NAME = 'Update FirstName'
LAST_NAME = 'LastName'
UPDATE_LAST_NAME = 'Update LastName'
TAG_NAME = 'lalala'

RESTRICTED_ENTITY_USERNAME = 'RestrictedEntityUser'
NOTES_USERNAME = 'NotesUser'

HIDDEN_USER_NEW_PASSWORD = 'test_pass_2'

TEMP_FILE_PREFIX = 'tfu_'

NOTE_COLUMN = 'Note'

JSON_ADAPTER_NAME = 'JSON File'
JSON_ADAPTER_SEARCH = 'json'
JSON_ADAPTER_PLUGIN_NAME = 'json_file_adapter'
WMI_INFO_ADAPTER = 'WMI Info'

AD_ADAPTER_NAME = 'Microsoft Active Directory (AD)'
CISCO_PRIME_ADAPTER_NAME = 'Cisco Prime'

STRESSTEST_ADAPTER = 'stresstest_adapter'
STRESSTEST_ADAPTER_NAME = 'Test adapters'
STRESSTEST_SCANNER_ADAPTER = 'stresstest_scanner_adapter'

ALERTLOGIC_ADAPTER = 'alertlogic_adapter'
ALERTLOGIC_ADAPTER_NAME = 'Alert Logic'

AWS_ADAPTER = 'aws_adapter'
AWS_ADAPTER_NAME = 'Amazon Web Services (AWS)'

SHODAN_ADAPTER = 'shodan_adapter'

WINDOWS_QUERY_NAME = 'Windows Operating System'
LINUX_QUERY_NAME = 'Linux Operating System'
AD_MISSING_AGENTS_QUERY_NAME = 'AD devices missing agents'
MANAGED_DEVICES_QUERY_NAME = 'Managed Devices'

HOSTNAME_DC_QUERY = 'specific_data.data.hostname == regex("dc", "i")'
HOSTNAME_DC_QUERY_NAME = 'DC Devices'
IPS_192_168_QUERY = 'specific_data.data.network_interfaces.ips == regex("192.168", "i")'
IPS_192_168_QUERY_NAME = 'IPs Subnet 192.168.0.0'

DEVICES_MODULE = 'Devices'
USERS_MODULE = 'Users'

OS_SERVICE_PACK_OPTION_NAME = 'OS: Service Pack'
IS_ADMIN_OPTION_NAME = 'Is Admin'
IS_LOCAL_OPTION_NAME = 'Is Local'
USER_NAME_OPTION_NAME = 'User Name'
AD_PRIMARY_GROUP_ID_OPTION_NAME = 'AD Primary group ID'
COUNT_OPTION_NAME = 'Count'
AVERAGE_OPTION_NAME = 'Average'
OS_TYPE_OPTION_NAME = 'OS: Type'
NETWORK_IPS_OPTION_NAME = 'IPs'
NETWORK_MAC_OPTION_NAME = 'MAC'
TAGS_OPTION_NAME = 'Tags'
ASSET_NAME_FIELD_NAME = 'Asset Name'
TAGS_FIELD_NAME = 'Tags'

DISCOVERY_DEFAULT_VALUE = '12'
DISCOVERY_UPDATED_VALUE = '8'


class EmailSettings:
    port = '25'
    host = 'services.axonius.lan'


class QueriesScreen:
    query_1 = 'adapters == size(1)'
    query_1_name = 'test_saved_query_1'


class Enforcements:
    enforcement_name_1 = 'test_enforcement_1'
    enforcement_query_1 = WINDOWS_QUERY_NAME


class Saml:
    idp = 'test_idp_1'
    cert = 'certificate'
    cert_content = 'certfilecontent'


class Notes:
    note1_text = 'note1_text'
    note1_device_filter = 'puppet-1'


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
