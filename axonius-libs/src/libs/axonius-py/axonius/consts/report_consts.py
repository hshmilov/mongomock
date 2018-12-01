from enum import Enum, auto

NO_CHANGE_DESCRIPTION = 'any results'
NEW_ENTITIES_DESCRIPTION = 'new entities were added'
PREVIOUS_ENTITIES = 'previous entities were removed'
ABOVE_DESCRIPTION = 'the number of entities is above {}'
BELOW_DESCRIPTION = 'the number of entities is below {}'
PERIOD_ALL_DESCRIPTION = 'every discovery cycle'
PERIOD_WEEKLY_DESCRIPTION = 'weekly'
PERIOD_DAILY_DESCRIPTION = 'daily'
PERIOD_MONTHLY_DESCRIPTION = 'monthly'


TRIGGERS_DIFF_ADDED = 'added'
TRIGGERS_DIFF_REMOVED = 'removed'

TRIGGERS_TO_DESCRIPTION = {'every_discovery': NO_CHANGE_DESCRIPTION,
                           'new_entities': NEW_ENTITIES_DESCRIPTION,
                           'previous_entities': PREVIOUS_ENTITIES,
                           'above': ABOVE_DESCRIPTION,
                           'below': BELOW_DESCRIPTION
                           }

PERIOD_TO_DESCRIPTION = {'all': PERIOD_ALL_DESCRIPTION,
                         'weekly': PERIOD_WEEKLY_DESCRIPTION,
                         'daily': PERIOD_DAILY_DESCRIPTION,
                         'monthly': PERIOD_MONTHLY_DESCRIPTION,
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


LOGOS_PATH = '/home/axonius/libs/axonius-py/axonius/assets'
