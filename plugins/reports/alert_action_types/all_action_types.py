from typing import Dict

from reports.alert_action_types.push_system_notification import SystemNotificationAction
from reports.alert_action_types.send_emails import SendEmailsAction
from reports.alert_action_types.send_https_log import SendHttpsLogAction
from reports.alert_action_types.send_syslog import NotifySyslogAction
from reports.action_types.create_servicenow_incident import ServiceNowIncidentAction
from reports.alert_action_types.alert_action_type_base import AlertActionTypeBase

AllAlertActionTypes: Dict[str, type(AlertActionTypeBase)] = {
    'create_notification': SystemNotificationAction,
    'send_emails': SendEmailsAction,
    'notify_syslog': NotifySyslogAction,
    'send_https_log': SendHttpsLogAction,
    'create_service_now_incident': ServiceNowIncidentAction
}
