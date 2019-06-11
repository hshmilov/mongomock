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

USERS_CONFIG_COLLECTION = 'users_config'

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
PREDEFINED_ROLE_READONLY = 'Read Only User'
PREDEFINED_ROLE_RESTRICTED = 'Restricted User'

####################
# Instances consts #
####################
LOGGED_IN_MARKER_PATH = AXONIUS_SETTINGS_PATH / '.logged_in'
ENCRYPTION_KEY_FILENAME = '.__key'
ENCRYPTION_KEY_PATH = AXONIUS_SETTINGS_PATH / ENCRYPTION_KEY_FILENAME
PROXY_DATA_FILE = 'proxy_data.json'  # do not modify! used in chef!
PROXY_DATA_PATH = AXONIUS_SETTINGS_PATH / PROXY_DATA_FILE

# Other consts
SPECIFIC_DATA = 'specific_data'
ADAPTERS_DATA = 'adapters_data'
PROXY_ERROR_MESSAGE = 'Bad proxy settings or no internet connection'

######################
# reports consts     #
######################

REPORTS_DELETED = 'reports_deleted'


class FeatureFlagsNames:
    TrialEnd = 'trial_end'
    LockedActions = 'locked_actions'


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
