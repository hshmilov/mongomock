from enum import Enum, auto
from pathlib import Path

from axonius.consts.plugin_consts import (AXONIUS_SETTINGS_DIR_NAME,
                                          ENCRYPTION_KEY_FILENAME)


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

EXEC_REPORT_THREAD_ID = 'exec_report_thread'

EXEC_REPORT_TITLE = 'Axonius Report'

EXEC_REPORT_FILE_NAME = 'Axonius Report.pdf'

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
AXONIOUS_SETTINGS_PATH = Path('/home/axonius/') / AXONIUS_SETTINGS_DIR_NAME
ENCRYPTION_KEY_PATH = AXONIOUS_SETTINGS_PATH / ENCRYPTION_KEY_FILENAME
LOGGED_IN_MARKER_PATH = AXONIOUS_SETTINGS_PATH / '.logged_in'

# Other consts
SPECIFIC_DATA = 'specific_data'
ADAPTERS_DATA = 'adapters_data'
PROXY_ERROR_MESSAGE = 'Bad proxy settings or no internet connection'


class FeatureFlagsNames:
    TrialEnd = 'trial_end'
    LockedActions = 'locked_actions'


class Signup:
    SignupCollection = 'signup'
    SignupField = 'signup'
    SignupEndpoint = 'signup'
    NewPassword = 'newPassword'
    ConfirmNewPassword = 'confirmNewPassword'
