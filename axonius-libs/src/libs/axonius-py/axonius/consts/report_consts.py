from enum import Enum, auto


class Triggers(Enum):
    """
    Possible case criteria's for reports and when they should execute the appropriate actions.
    """
    Increase = auto()
    Decrease = auto()
    Above = auto()
    Below = auto()
    No_Change = auto()


class Actions(Enum):
    Create_Notification = auto()
    Send_Mail = auto()
    Tag_Devices = auto()


REPORT_TITLE = "Axonius Alert for Query: {query_name}"

REPORT_CONTENT_HTML = """\
<html>
  <head></head>
  <body>
    <p>An alert for the following query has been triggered: {query_name}<br><br>
       <b>Alert Details</b><br>
       Number of times this alert has been triggered:{num_of_triggers}<br>
       The alert was triggered because:the number of devices has {trigger_message}<br>
       The number of devices returned by the query:{num_of_current_devices}<br>
       The previous number of devices was:{old_results_num_of_devices}<br><br>
       You can watch the query and its results here:<a href="{query_link}">Link</a>
    </p>
  </body>
</html>
"""

REPORT_CONTENT = "An alert for the following query has been triggered: {query_name}\n\nAlert Details\nNumber of times this alert has been triggered:{num_of_triggers}\nThe alert was triggered because:the number of devices has {trigger_message}\nThe number of devices returned by the query:{num_of_current_devices}\nThe previous number of devices was:{old_results_num_of_devices}\n\nYou can view the query and its results here:{query_link}"
