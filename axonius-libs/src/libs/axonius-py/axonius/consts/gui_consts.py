from enum import Enum, auto

from axonius.consts.plugin_consts import AXONIUS_SETTINGS_PATH


class ChartMetrics(Enum):
    """
    Possible scales of data to represent using a chart
    """
    compare = auto()
    intersect = auto()
    segment = auto()
    abstract = auto()
    timeline = auto()


class ChartViews(Enum):
    """
    Possible representations for charts
    """
    histogram = auto()
    pie = auto()
    summary = auto()
    line = auto()


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
FEATURE_FLAGS_CONFIG = 'FeatureFlags'

######################
# Users consts #
######################

USERS_CONFIG_COLLECTION = 'users_config'
UNCHANGED_MAGIC_FOR_GUI = ['unchanged']


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

####################
# User Preferences #
####################
USERS_PREFERENCES_COLLECTION = 'users_preferences'
USERS_PREFERENCES_COLUMNS_FIELD = 'table_columns'
USERS_PREFERENCES_DEFAULT_FIELD = 'default'

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
PROXY_ERROR_MESSAGE = 'Bad proxy settings or no internet connection'

GETTING_STARTED_CHECKLIST_SETTING = 'getting_started_checklist'
SPECIFIC_DATA_CONNECTION_LABEL = f'{SPECIFIC_DATA}.connection_label'
SPECIFIC_DATA_CLIENT_USED = f'{SPECIFIC_DATA}.client_used'
SPECIFIC_DATA_PLUGIN_UNIQUE_NAME = f'{SPECIFIC_DATA}.plugin_unique_name'


class FeatureFlagsNames:
    TrialEnd = 'trial_end'
    LockedActions = 'locked_actions'
    ExperimentalAPI = 'experimental_api'
    CloudCompliance = 'cloud_compliance'
    ExpiryDate = 'expiry_date'
    LockOnExpiry = 'lock_on_expiry'
    ReenterCredentials = 'reenter_credentials'
    RefetchAssetEntityAction = 'refetch_action'


class CloudComplianceNames:
    Enabled = 'cis_enabled'
    Visible = 'enabled'


class RootMasterNames:
    root_key = 'root_master_settings'
    enabled = 'enabled'
    delete_backups = 'delete_backups'


class Signup:
    SignupCollection = 'signup'
    SignupField = 'signup'
    SignupEndpoint = 'signup'
    NewPassword = 'newPassword'
    ConfirmNewPassword = 'confirmNewPassword'  # do not change this const!
    CompanyField = 'companyName'  # do not change this const!
    ContactEmailField = 'contactEmail'  # do not change this const!
    UserName = 'userName'


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

LAST_UPDATED_FIELD = 'last_updated'
UPDATED_BY_FIELD = 'updated_by'
PREFERRED_FIELDS = ('specific_data.data.hostname_preferred',
                    'specific_data.data.os.type_preferred',
                    'specific_data.data.os.distribution_preferred',
                    'specific_data.data.network_interfaces.mac_preferred',
                    'specific_data.data.network_interfaces.ips_preferred')
ADAPTER_CONNECTIONS_FIELD = 'Adapter Connections'
DISTINCT_ADAPTERS_COUNT_FIELD = 'Distinct Adapter Connections Count'

#########################
# Common Values #
#########################

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
EXCLUDED_CSRF_ENDPOINTS = ('/api/login', '/api/signup', 'api/login/ldap', 'api/login/saml')
