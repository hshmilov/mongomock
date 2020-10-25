from enum import Enum, auto

from axonius.consts.plugin_consts import AXONIUS_SETTINGS_PATH, PLUGIN_UNIQUE_NAME


class ChartMetrics(Enum):
    """
    Possible scales of data to represent using a chart
    """
    compare = auto()
    intersect = auto()
    segment = auto()
    segment_timeline = auto()
    adapter_segment = auto()
    abstract = auto()
    timeline = auto()
    matrix = auto()


class ChartViews(Enum):
    """
    Possible representations for charts
    """
    histogram = auto()
    adapter_histogram = auto()
    pie = auto()
    summary = auto()
    line = auto()
    stacked = auto()


class ChartFuncs(Enum):
    """
    Possible functions to run on a field list of values, as returned from some query
    """
    average = auto()
    count = auto()


class ChartRangeTypes(Enum):
    """
    Possible types of a timeframe range for the timeline chart
    """
    absolute = auto()
    relative = auto()


class ChartRangeUnits(Enum):
    """
    Possible units for defining a relative timeframe
    """
    day = auto()
    week = auto()
    month = auto()
    year = auto()


RANGE_UNIT_DAYS = {
    ChartRangeUnits.day: 1,
    ChartRangeUnits.week: 7,
    ChartRangeUnits.month: 30,
    ChartRangeUnits.year: 365
}


class ResearchStatus(Enum):
    """
    Possible status for research usability - could take time to start / stop so we want to keep the user posted
    """
    starting = auto()
    running = auto()
    stopping = auto()
    done = auto()


CONFIG_CONFIG = 'GuiService'
GUI_CONFIG_NAME = 'GuiService'  # duplicate of the above because i'd like to have a normal name
FEATURE_FLAGS_CONFIG = 'FeatureFlags'
IDENTITY_PROVIDERS_CONFIG = 'IdentityProviders'

LATEST_VERSION_URL = 'https://releases.pub.axonius.com/v1/latest-version-name'
INSTALLED_VERISON_KEY = 'Installed Version'
######################
# Users consts #
######################

USERS_CONFIG_COLLECTION = 'users_config'
UNCHANGED_MAGIC_FOR_GUI = ['unchanged']

#############################
# Identity providers consts #
#############################

ROLE_ASSIGNMENT_RULES = 'role_assignment_rules'
DEFAULT_ROLE_ID = 'default_role_id'
EVALUATE_ROLE_ASSIGNMENT_ON = 'evaluate_role_assignment_on'
ASSIGNMENT_RULE = 'assignment_rule'
ASSIGNMENT_RULE_ARRAY = 'rules'
ASSIGNMENT_RULE_TYPE = 'type'
ASSIGNMENT_RULE_KEY = 'key'
ASSIGNMENT_RULE_VALUE = 'value'
ASSIGNMENT_RULE_ROLE_ID = 'role_id'

NEW_USERS_ONLY = 'New users only'
NEW_AND_EXISTING_USERS = 'New and existing users'

ROLES_SOURCE = {
    'key': 'all-roles',
    'options': {
        'allow-custom-option': False
    }
}


DEFAULT_ASSIGNMENT_RULE_SCHEMA = [
    {
        'name': ASSIGNMENT_RULE_VALUE,
        'title': 'Value',
        'placeholder': 'Value',
        'type': 'string',
        'errorMsg': 'Role assignment rule - missing value'
    },
    {
        'name': ASSIGNMENT_RULE_ROLE_ID,
        'title': ' Role name',
        'placeholder': 'Role',
        'type': 'string',
        'enum': [],
        'source': ROLES_SOURCE
    },
]

EVALUATE_ROLE_ASSIGNMENT_ON_SCHEMA = {
    'name': EVALUATE_ROLE_ASSIGNMENT_ON,
    'title': 'Evaluate role assignment on ',
    'type': 'string',
    'enum': [NEW_USERS_ONLY, NEW_AND_EXISTING_USERS],
    'default': 'New users only',
}


EMAIL_ADDRESS = 'Email address'
EMAIL_DOMAIN = 'Email domain'
LDAP_GROUP = 'Group'

######################
# Exec report consts #
######################

EXEC_REPORT_THREAD_ID = 'exec_report_thread_{}'

EXEC_REPORT_GENERATE_PDF_THREAD_ID = 'exec_report_generate_pdf_thread_{}'

EXEC_REPORT_TITLE = 'Axonius Report'

EXEC_REPORT_FILE_NAME = 'Axonius Report {}.pdf'

EXEC_REPORT_EMAIL_CONTENT = '''Hello,

this is a periodic report sent to you by axonius.
To change the intervals in which the report is being sent or remove yourself from the recipients of this email please
enter reporting in Axonius.'''

TEMP_MAINTENANCE_THREAD_ID = 'support_access_thread'

#########################
# User and Roles consts #
#########################

USERS_COLLECTION = 'users'
ROLES_COLLECTION = 'roles'
PREDEFINED_ROLE_ADMIN = 'Admin'
PREDEFINED_ROLE_OWNER = 'Owner'
PREDEFINED_ROLE_OWNER_RO = 'OwnerReadOnly'
PREDEFINED_ROLE_VIEWER = 'Viewer'
# Old viewer role name
PREDEFINED_ROLE_READONLY = 'Read Only User'
# Old restricted role name
PREDEFINED_ROLE_RESTRICTED_USER = 'Restricted User'
PREDEFINED_ROLE_RESTRICTED = 'Restricted'
IS_AXONIUS_ROLE = 'is_axonius_role'
IS_API_USER = 'is_api_user'
NO_ACCESS_ROLE = 'No Access'

####################
# User Preferences #
####################
USERS_PREFERENCES_COLLECTION = 'users_preferences'
USERS_PREFERENCES_COLUMNS_FIELD = 'table_columns'
USERS_PREFERENCES_DEFAULT_FIELD = 'default'

###############
# User tokens #
###############
USERS_TOKENS_COLLECTION_TTL_INDEX_NAME = 'date_added'
USERS_TOKENS_COLLECTION = 'users_token'
USERS_TOKENS_RESET_LINK = 'https://{server_name}/login?token={token}'
USERS_TOKENS_EMAIL_INVITE_SUBJECT = 'Welcome to Axonius'
USERS_TOKENS_EMAIL_SUBJECT = 'Axonius Password Reset'
USERS_TOKENS_RESET_EMAIL_CONTENT = '''Dear Axonius user,

We've received a request from your Axonius administrator to reset your password. If you didn't make the request, just ignore this email.
Otherwise, you can reset your password using this link:
{link}

The password reset link will expire in {expire_hours} hours.

Thanks,
Axonius'''
USERS_TOKENS_INVITE_EMAIL_CONTENT = '''Dear Axonius user,

An Axonius administrator has invited you to the Axonius Cybersecurity Asset Management Platform. Your username is: {user_name}.
To accept the invitation and to create your password, use the following link: {link}
The invite will expire in {expire_hours} hours.

Thank you,
Axonius'''

####################
# Instances consts #
####################
LOGGED_IN_MARKER_PATH = AXONIUS_SETTINGS_PATH / '.logged_in'
ENCRYPTION_KEY_FILENAME = '.__key'
ENCRYPTION_KEY_PATH = AXONIUS_SETTINGS_PATH / ENCRYPTION_KEY_FILENAME
PROXY_DATA_FILE = 'proxy_data.json'  # do not modify! used in chef!
PROXY_DATA_PATH = AXONIUS_SETTINGS_PATH / PROXY_DATA_FILE  # do not modify! used in chef!

# Other consts
SPECIFIC_DATA = 'specific_data'
ADAPTERS_DATA = 'adapters_data'
ADAPTERS_META = 'adapters_meta'
CORRELATION_REASONS = 'correlation_reasons'
HAS_NOTES = 'has_notes'
HAS_NOTES_TITLE = 'Has Notes'
PROXY_ERROR_MESSAGE = 'Bad proxy settings or no internet connection'

GETTING_STARTED_CHECKLIST_SETTING = 'getting_started_checklist'
SPECIFIC_DATA_CONNECTION_LABEL = f'{SPECIFIC_DATA}.connection_label'
CLIENT_USED = 'client_used'
SPECIFIC_DATA_CLIENT_USED = f'{SPECIFIC_DATA}.{CLIENT_USED}'
SPECIFIC_DATA_PLUGIN_UNIQUE_NAME = f'{SPECIFIC_DATA}.{PLUGIN_UNIQUE_NAME}'


class FeatureFlagsNames:
    TrialEnd = 'trial_end'
    LockedActions = 'locked_actions'
    Bandicoot = 'bandicoot'
    ExperimentalAPI = 'experimental_api'
    BandicootCompare = 'bandicoot_result_compare_only'
    CloudCompliance = 'cloud_compliance'
    ExpiryDate = 'expiry_date'
    LockOnExpiry = 'lock_on_expiry'
    ReenterCredentials = 'reenter_credentials'
    RefetchAssetEntityAction = 'refetch_action'
    EnableFIPS = 'enable_fips'
    EnableSaaS = 'enable_saas'
    DisableRSA = 'disable_rsa'
    HigherCiphers = 'higher_ciphers'
    DoNotUseSoftwareNameAndVersionField = 'do_not_use_software_name_and_version_field'
    DoNotPopulateHeavyFields = 'do_not_populate_heavy_fields'
    PopulateMajorMinorVersionFields = 'populate_major_minor_version_fields'
    QueryTimelineRange = 'query_timeline_range'
    EnforcementCenter = 'enforcement_center'


class CloudComplianceNames:
    Enabled = 'cis_enabled'
    Visible = 'enabled'
    ExpiryDate = 'expiry_date'


class RootMasterNames:
    root_key = 'root_master_settings'
    enabled = 'enabled'
    delete_backups = 'delete_backups'


class ParallelSearch:
    root_key = 'parallel_search'
    enabled = 'enabled'


class DashboardControlNames:
    root_key = 'dashboard_control'
    present_call_limit = 'present_call_limit'
    historical_call_limit = 'historical_call_limit'


class Signup:
    SignupCollection = 'signup'
    SignupField = 'signup'
    SignupEndpoint = 'signup'
    NewPassword = 'newPassword'
    ConfirmNewPassword = 'confirmNewPassword'  # do not change this const!
    CompanyField = 'companyName'  # do not change this const!
    ContactEmailField = 'contactEmail'  # do not change this const!
    UserName = 'userName'
    ApiKeysField = 'api_keys'


class GuiCache:
    root_key = 'cache_settings'
    enabled = 'enabled'
    ttl = 'ttl'


# DO NOT MOVE THESE CREDS FROM THIS FILE. we need the in test AND prod AND inside the docker!
SIGNUP_TEST_CREDS = {Signup.CompanyField: 'test_company',
                     Signup.NewPassword: 'cAll2SecureAll',
                     Signup.ContactEmailField: 'a@b.com',
                     Signup.UserName: 'admin'
                     }
SIGNUP_TEST_COMPANY_NAME = 'singnup_test_company_name'

#########################
# Dashboard consts #
#########################

DASHBOARD_COLLECTION = 'dashboard'
DASHBOARD_SPACES_COLLECTION = 'dashboard_spaces'
DASHBOARD_SPACE_DEFAULT = 'Axonius Dashboard'
DASHBOARD_SPACE_PERSONAL = 'My Dashboard'
DASHBOARD_SPACE_TYPE_DEFAULT = 'default'
DASHBOARD_SPACE_TYPE_PERSONAL = 'personal'
DASHBOARD_SPACE_TYPE_CUSTOM = 'custom'
DASHBOARD_LIFECYCLE_ENDPOINT = 'lifecycle'

#########################
# Field names #
#########################

DEFAULT_FIELDS = 'adapters,specific_data.data.name,specific_data.data.hostname,' \
    'specific_data.data.last_seen,specific_data.data.network_interfaces.mac,' \
    'specific_data.data.network_interfaces.ips,specific_data.data.os.type,labels'

LAST_UPDATED_FIELD = 'last_updated'
UPDATED_BY_FIELD = 'updated_by'
PREFERRED_FIELDS = ('specific_data.data.hostname_preferred',
                    'specific_data.data.os.type_preferred',
                    'specific_data.data.os.distribution_preferred',
                    'specific_data.data.os.os_str_preferred',
                    'specific_data.data.os.bitness_preferred',
                    'specific_data.data.os.kernel_version_preferred',
                    'specific_data.data.os.build_preferred',
                    'specific_data.data.network_interfaces.mac_preferred',
                    'specific_data.data.network_interfaces.ips_preferred',
                    'specific_data.data.network_interfaces.locations_preferred',
                    'specific_data.data.device_model_preferred',
                    'specific_data.data.domain_preferred')
ADAPTER_CONNECTIONS_FIELD = 'Adapter Connections'
DISTINCT_ADAPTERS_COUNT_FIELD = 'Distinct Adapter Connections Count'
LABELS_FIELD = 'labels'

#########################
# Common Values #
#########################

USER_NAME = 'user_name'
ROLE_ID = 'role_id'
USER_ID_FIELD = 'user_id'
IGNORE_ROLE_ASSIGNMENT_RULES = 'ignore_role_assignment_rules'
PRIVATE_FIELD = 'private'
PREDEFINED_FIELD = 'predefined'
PREDEFINED_PLACEHOLDER = 'Predefined'
JSONIFY_DEFAULT_TIME_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'
FILE_NAME_TIMESTAMP_FORMAT = '%Y-%m-%dT%H-%M-%SUTC'
MAX_DAYS_SINCE_LAST_SEEN = 60

MAX_SORTED_FIELDS = ['specific_data.data.last_seen',
                     'specific_data.data.fetch_time',
                     'specific_data.data.last_seen_in_devices',
                     'specific_data.data.last_lockout_time',
                     'specific_data.data.last_bad_logon',
                     'specific_data.data.last_password_change',
                     'specific_data.data.last_logoff',
                     'specific_data.data.last_logon',
                     'specific_data.data.last_logon_timestamp']

MIN_SORTED_FIELDS = ['specific_data.data.first_seen',
                     'specific_data.data.first_fetch_time',
                     'specific_data.data.password_expiration_date',
                     'specific_data.data.account_expires']

CORRELATION_REASONS_FIELD = 'specific_data.data.correlation_reasons'

SPECIFIC_DATA_PREFIX_LENGTH = len('specific_data.data.')
# sha256 of AxoniusForTheWin!!!
HASH_SALT = '2098f251e4f9d93cd379de4184e7eef17817fbc504e03ded3d6f09364d7725a3'

#########################
# CSRF Values #
#########################
CSRF_TOKEN_LENGTH = 64
EXCLUDED_CSRF_ENDPOINTS = ('api/login', 'api/signup', 'api/login/ldap', 'api/login/saml',
                           'settings/users/tokens/reset', 'api/devices', 'api/users')


#################
# Activity Logs #
#################

ACTIVITY_PARAMS_ARG = 'activity_params'
SKIP_ACTIVITY_ARG = 'skip_activity'
ACTIVITY_PARAMS_COUNT = 'count'
ACTIVITY_PARAMS_NAME = 'name'
IS_INSTANCES_MODE = 'is_instances_mode'
INSTANCE_NAME = 'instance_name'
INSTANCE_PREV_NAME = 'instance_prev_name'


class SortType(Enum):
    """
    Sort type to sort the dashboard chart data by.
    """
    VALUE = 'value'
    NAME = 'name'


class SortOrder(Enum):
    """
    Sort order to sort the dashboard chart data by.
    """
    DESC = 'desc'
    ASC = 'asc'


class Action(Enum):
    send_emails = 'Send Email'
    send_csv_to_s3 = 'Send CSV to Amazon S3'
    create_notification = 'Push System Notification'
    carbonblack_isolate = 'Isolate in VMware Carbon Black EDR'
    cybereason_isolate = 'Isolate in Cybereason Deep Detect & Respond'
    cybereason_unisolate = 'Unisolate in Cybereason Deep Detect & Respond'
    cybereason_tag = 'Tag in Cybereason Deep Detect & Respond'
    notify_syslog = 'Send to Syslog System'
    tag = 'Add Tag'
    untag = 'Remove Tag'
    run_executable_windows = 'Deploy on Windows Device'
    run_wmi_scan = 'Run WMI Scan'
    run_windows_shell_command = 'Deploy Files and Run Windows Shell Command'
    run_linux_ssh_scan = 'Run Linux SSH Scan'
    shodan_enrichment = 'Enrich Device Data with Shodan'
    censys_enrichment = 'Enrich Device Data with Censys'
    webscan_enrichment = 'Enrich Device Data with Web Server Information'
    scan_with_qualys = 'Add to Qualys Cloud Platform'
    change_ldap_attribute = 'Update LDAP Attributes of Users or Devices'
    ScanTenable = 'Add to Tenable'
    carbonblack_defense_change_policy = 'Change VMware Carbon Black Cloud Policy'
    carbonblack_defense_quarantine = 'Isolate VMware Carbon Black Cloud Device'
    carbonblack_defense_unquarantine = 'Unisolate VMware Carbon Black Cloud Device'
    desktop_central_do_som_action = 'Manage Computer in ManageEngine Desktop Central SoM'
    tenable_sc_add_ips_to_asset = 'Add IPs to Tenable.sc Asset'
    tenable_io_add_ips_to_target_group = 'Add IPs to Tenable.io Target Group'
    create_jira_incident = 'Create Jira Issue'
    add_custom_data = 'Add Custom Data'


class ActionCategory:
    Run = 'Deploy Files and Run Commands'
    Notify = 'Notify'
    Isolate = 'Execute Endpoint Security Agent Action'
    Enrichment = 'Enrich Device or User Data'
    Utils = 'Axonius Utilities'
    Scan = 'Add Device to VA Scan'
    Patch = 'Patch Device'
    ManageAD = 'Manage Microsoft Active Directory (AD) Services'
    Incident = 'Create Incident'
    Block = 'Block Device in Firewall'
    DNS = 'Manage DNS Services'


class TunnelStatuses:
    not_available = 'not_available'  # this is not a saas machine
    never_connected = 'never_connected'  # this is a saas machine, never connected to tunnel
    connected = 'connected'  # this is a saas machine, connected to tunnel
    disconnected = 'disconnected'  # this is a saas machine, disconnected from tunnel


# Saved Queries
DEVICES_DIRECT_REFERENCES_COLLECTION = 'device_views_direct'
USERS_DIRECT_REFERENCES_COLLECTION = 'user_views_direct'
DEVICES_INDIRECT_REFERENCES_COLLECTION = 'device_views_indirect'
USERS_INDIRECT_REFERENCES_COLLECTION = 'user_views_indirect'
# pylint: disable=anomalous-backslash-in-string
SAVED_QUERY_PLACEHOLDER_REGEX = '{{QueryID=(\w+)}}'
PREDEFINED_SAVED_QUERY_REF_REGEX = '{{QueryID=<QUERY_NAME=([a-zA-Z0-9_\-\s]+)>}}'
OS_DISTRIBUTION_GT_LT_QUERY_REGEX = r'os\.distribution\s([<>])\s"(.+?)"'
