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


REPORT_TITLE = "Axonius Report For Query: {query_name}"

REPORT_CONTENT_HTML = """\
<html>
  <head></head>
  <body>
    <p><span style="text-transform: uppercase;">{severity}:</span> A Report For query: {query_name} has been triggered<br>
       This is the {num_of_triggers} time this has happened.<br>
       It was triggered because the number of devices has {trigger_message}.<br>
       The number of devices returned by the query is {num_of_current_devices}.
    </p>
  </body>
</html>
"""

REPORT_CONTENT = "A Report For query: {query_name} has been triggered.\n This is the {num_of_triggers} time this has happened.\n It was triggered because the number of devices has {trigger_message}.\nThe number of devices returned by the query is {num_of_current_devices}."
