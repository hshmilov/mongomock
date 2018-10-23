from enum import Enum, auto


NO_CHANGE_DESCRIPTION = 'requested to alert every discovery cycle'
NEW_ENTITIES_DESCRIPTION = 'new entites were added'
PREVIOUS_ENTITIES = 'previous entities were removed'
ABOVE_DESCRIPTION = 'the number of entities is above {}'
BELOW_DESCRIPTION = 'the number of entities is below {}'


TRIGGERS_DIFF_TYPES = ['last_result', 'added', 'removed']

TRIGGERS_TO_DESCRIPTION = {'every_discovery': NO_CHANGE_DESCRIPTION,
                           'new_entities': NEW_ENTITIES_DESCRIPTION,
                           'previous_entities': PREVIOUS_ENTITIES,
                           'above': ABOVE_DESCRIPTION,
                           'below': BELOW_DESCRIPTION
                           }

TRIGGERS_DEFAULT_VALUES = {'every_discovery': False,
                           'new_entities': False,
                           'previous_entities': False,
                           'above': 0,
                           'below': 0,
                           }


class Actions(Enum):
    Create_Notification = auto()
    Send_Mail = auto()
    Tag_Devices = auto()


SERVICE_NOW_SEVERITY = {
    'info': 3,
    'warning': 2,
    'error': 1
}

REPORT_TITLE = 'Axonius Alert - "{name}" for Query: {query}'

REPORT_CONTENT_HTML = '''\
<html>
  <head></head>
  <body>
    <p>Alert - "{name}" for the following query has been triggered: {query}<br><br>
       <b>Alert Details</b><br>
       Number of times this alert has been triggered: {num_of_triggers}<br>
       The alert was triggered because: {trigger_message}<br>
       The number of devices returned by the query: {num_of_current_devices}<br>
       The previous number of devices was: {old_results_num_of_devices}<br><br>
       You can watch the query and its results here:<br><a href="{query_link}">Link</a>
    </p>
  </body>
</html>
'''

REPORT_CONTENT = \
    '''Alert - "{name}" for the following query has been triggered: {query}

Alert Details
Number of times this alert has been triggered:{num_of_triggers}
The alert was triggered because: {trigger_message}
The number of devices returned by the query:{num_of_current_devices}
The previous number of devices was:{old_results_num_of_devices}

You can view the query and its results here:{query_link}'''

FRESH_SERVICE_PRIORITY = {
    'low': 1,
    'medium': 2,
    'high': 3,
    'urgent': 4
}
