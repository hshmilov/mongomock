from typing import Dict

from reports.action_types.action_type_base import ActionTypeBase
from reports.action_types.base.carbonblack_isolate import CarbonblackIsolateAction
from reports.action_types.base.carbonblack_unisolate import CarbonblackUnisolateAction
from reports.action_types.base.create_servicenow_computer import ServiceNowComputerAction
from reports.action_types.base.run_cmd import RunCmd
from reports.action_types.base.run_executable import RunExecutable
from reports.action_types.base.tag_all_entities import TagAllEntitiesAction
from reports.action_types.base.untag_all_entities import UntagAllEntitiesAction
from reports.action_types.alert.push_system_notification import SystemNotificationAction
from reports.action_types.alert.send_emails import SendEmailsAction
from reports.action_types.alert.send_https_log import SendHttpsLogAction
from reports.action_types.alert.send_syslog import NotifySyslogAction
from reports.action_types.base.create_servicenow_incident import ServiceNowIncidentAction


AllActionTypes: Dict[str, type(ActionTypeBase)] = {
    'create_service_now_computer': ServiceNowComputerAction,
    'tag': TagAllEntitiesAction,
    'carbonblack_isolate': CarbonblackIsolateAction,
    'carbonblack_unisolate': CarbonblackUnisolateAction,
    'untag': UntagAllEntitiesAction,
    'run_executable_windows': RunExecutable,
    'run_command_windows': RunCmd,
    'create_notification': SystemNotificationAction,
    'send_emails': SendEmailsAction,
    'notify_syslog': NotifySyslogAction,
    'send_https_log': SendHttpsLogAction,
    'create_service_now_incident': ServiceNowIncidentAction
}
