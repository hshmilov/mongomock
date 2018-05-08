from enum import Enum, auto


class ChartTypes(Enum):
    """
    Possible phases of the system.
    Currently may be Research, meaning fetch and calculate are running, or Stable, meaning nothing is being changed.
    """
    compare = auto()
    intersect = auto()

# Exec report consts


EXEC_REPORT_THREAD_ID = 'exec_report_thread'

EXEC_REPORT_TITLE = 'Axonius Report'

EXEC_REPORT_FILE_NAME = 'Axonius Report.pdf'

EXEC_REPORT_EMAIL_CONTENT = """Hello,

this is a periodic report sent to you by axonius.
To change the intervals in which the report is being sent or remove yourself from the recipients of this email please enter reporting in Axonius."""
