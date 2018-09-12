from enum import Enum, auto


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


class ResearchStatus(Enum):
    """
    Possible status for research usability - could take time to start / stop so we want to keep the user posted
    """
    starting = auto()
    running = auto()
    stopping = auto()
    done = auto()


######################
# Exec report consts #
######################

EXEC_REPORT_THREAD_ID = 'exec_report_thread'

EXEC_REPORT_TITLE = 'Axonius Report'

EXEC_REPORT_FILE_NAME = 'Axonius Report.pdf'

EXEC_REPORT_EMAIL_CONTENT = """Hello,

this is a periodic report sent to you by axonius.
To change the intervals in which the report is being sent or remove yourself from the recipients of this email please enter reporting in Axonius."""

SUPPORT_ACCESS_THREAD_ID = 'support_access_thread'
