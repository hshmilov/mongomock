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
SYSTEM_SCHEDULER_LOG_PATH = os.path.join(LOGS_PATH_HOST, 'system-scheduler', 'system_scheduler.axonius.log')

RESTRICTED_USERNAME = 'RestrictedUser'
VIEWER_USERNAME = 'ViewerUser'
VIEWER_ADDER_USERNAME = 'ViewerAdderUser'
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
JSON_FILE = 'json_file'
JSON_ADAPTER_SEARCH = 'json'
JSON_ADAPTER_PLUGIN_NAME = 'json_file_adapter'

AD_ADAPTER_NAME = 'Microsoft Active Directory (AD)'
WMI_ADAPTER_NAME = 'Windows Management Instrumentation (WMI)'
CISCO_PRIME_ADAPTER_NAME = 'Cisco Prime'


CSV_NAME = 'CSV'
CSV_PLUGIN_NAME = 'csv_adapter'

STRESSTEST_ADAPTER = 'stresstest_adapter'
STRESSTEST_ADAPTER_NAME = 'Test adapters'
STRESSTEST_SCANNER_ADAPTER = 'stresstest_scanner_adapter'
STRESSTEST_SCANNER_ADAPTER_NAME = 'Test adapters for scanners'
ALERTLOGIC_ADAPTER = 'alertlogic_adapter'
ALERTLOGIC_ADAPTER_NAME = 'Alert Logic'
WMI_INFO_ADAPTER = 'wmi_adapter'

AWS_ADAPTER = 'aws_adapter'
AWS_ADAPTER_NAME = 'Amazon Web Services (AWS)'
AZURE_ADAPTER = 'azure_adapter'
AZURE_ADAPTER_NAME = 'Microsoft Azure'

CROWD_STRIKE_ADAPTER = 'crowd_strike_adapter'
CROWD_STRIKE_ADAPTER_NAME = 'CrowdStrike Falcon'

SHODAN_ADAPTER = 'shodan_adapter'

TANIUM_SQ_ADAPTER = 'Tanium Interact'
TANIUM_DISCOVERY_ADAPTER = 'Tanium Discover'
TANIUM_ASSET_ADAPTER = 'Tanium Asset'

OKTA_ADAPTER = 'okta_adapter'
OKTA_ADAPTER_NAME = 'Okta'

WINDOWS_QUERY_NAME = 'Windows Operating System'
LINUX_QUERY_NAME = 'Linux Operating System'
AD_MISSING_AGENTS_QUERY_NAME = 'AD devices missing agents'
MANAGED_DEVICES_QUERY_NAME = 'Managed Devices'
MANAGED_DEVICES_QUERY = '(specific_data.data.adapter_properties == "Agent") ' \
                        'or (specific_data.data.adapter_properties == "Manager")'
UNMANAGED_DEVICES_QUERY_NAME = 'Unmanaged Devices'
DEVICES_NOT_SEEN_IN_LAST_30_DAYS_QUERY_NAME = 'Devices not seen in last 30 days'
DEVICES_SEEN_IN_LAST_7_DAYS_QUERY_NAME = 'Devices seen in last 7 days'
DEVICES_SEEN_IN_LAST_7_DAYS_QUERY = '(specific_data.data.last_seen >= date("NOW - 7d"))'

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

S3_DEVICES_BACKUP_FILE_NAME = 'devices_file_name'
S3_USERS_BACKUP_FILE_NAME = 'users_file_name'

CSV_ADAPTER_FILTER = 'adapters == "csv_adapter"'
LABEL_CLIENT_WITH_SAME_ID = 'client_with_same_id'

DEVICES_SEEN_NEGATIVE_VALUE_QUERY = '(adapters_data.json_file_adapter.last_seen <= date("NOW - 1d"))'

MASTER_NODE_NAME = 'Master'


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
    note1_device_filter = 'storageserver-avidor'


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


SPECIFIC_SEARCH_TYPES = {
    'host_name': 'Host Name',
    'last_used_users': 'Last Used Users',
    'ip_address': 'IP Address',
    'installed_software_name': 'Installed Software Name',
}


class ScheduleTriggers:
    every_x_days = 'Every x days'
    every_x_hours = 'Every x hours'
    every_week_days = 'Days of week'
