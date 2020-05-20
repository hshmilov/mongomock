from enum import Enum, auto

PERIOD_ALL_DESCRIPTION = 'every discovery cycle'
PERIOD_WEEKLY_DESCRIPTION = 'weekly'
PERIOD_DAILY_DESCRIPTION = 'daily'
PERIOD_MONTHLY_DESCRIPTION = 'monthly'

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
The alert was triggered because: {trigger_message}
The number of devices returned by the query:{num_of_current_devices}
The previous number of devices was:{old_results_num_of_devices}

You can view the query and its results here: {query_link}'''

FRESH_SERVICE_PRIORITY = {
    'low': 1,
    'medium': 2,
    'high': 3,
    'urgent': 4
}

LOGOS_PATH = '/home/axonius/libs/axonius-py/axonius/assets'


##########
# FIELDS #
##########

ACTION_FIELD = 'action'
ACTIONS_FIELD = 'actions'
ACTION_CONFIG_FIELD = 'config'
ACTIONS_MAIN_FIELD = 'main'
ACTIONS_SUCCESS_FIELD = 'success'
ACTIONS_FAILURE_FIELD = 'failure'
ACTIONS_POST_FIELD = 'post'
LAST_TRIGGERED_FIELD = 'last_triggered'
LAST_GENERATED_FIELD = 'last_generated'
TIMES_TRIGGERED_FIELD = 'times_triggered'
LAST_UPDATE_FIELD = 'last_updated'
TRIGGERS_FIELD = 'triggers'
TRIGGER_VIEW_NAME_FIELD = f'{TRIGGERS_FIELD}.view.name'
TRIGGER_RESULT_VIEW_NAME_FIELD = 'result.metadata.trigger.view.name'


NOT_RAN_STATE = 'Not ran'
