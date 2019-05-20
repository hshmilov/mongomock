from typing import Dict

from reports.action_types.action_type_base import ActionTypeBase
from reports.action_types.alert.create_jira_incident import JiraIncidentAction
from reports.action_types.alert.create_servicenow_incident import ServiceNowIncidentAction
from reports.action_types.alert.create_sysaid_incident import SysaidIncidentAction
from reports.action_types.alert.push_system_notification import SystemNotificationAction
from reports.action_types.alert.send_csv_to_share import SendCsvToShare
from reports.action_types.alert.send_csv_to_s3 import SendCsvToS3
from reports.action_types.alert.send_emails import SendEmailsAction
from reports.action_types.alert.send_https_log import SendHttpsLogAction
from reports.action_types.alert.send_slack_message import SlackSendMessageAction
from reports.action_types.alert.send_syslog import NotifySyslogAction
from reports.action_types.base.carbonblack_defense_change_policy import CarbonblackDefenseChangePolicyAction
from reports.action_types.base.carbonblack_isolate import CarbonblackIsolateAction
from reports.action_types.base.carbonblack_unisolate import CarbonblackUnisolateAction
from reports.action_types.base.create_servicenow_computer import ServiceNowComputerAction
from reports.action_types.base.create_servicenow_incident_per_entity import ServiceNowIncidentPerEntity
from reports.action_types.base.cybereason_isolate import CybereasonIsolateAction
from reports.action_types.base.cybereason_unisolate import CybereasonUnisolateAction
from reports.action_types.base.disable_entity import DisableEntities
from reports.action_types.base.enable_entity import EnableEntities
from reports.action_types.base.run_cmd import RunCmd
from reports.action_types.base.run_executable import RunExecutable
from reports.action_types.base.run_linux_ssh_scan import RunLinuxSSHScan
from reports.action_types.base.run_wmi_scan import RunWMIScan
from reports.action_types.base.send_email_to_entities import SendEmailToEntities
from reports.action_types.base.tag_all_entities import TagAllEntitiesAction
from reports.action_types.base.tenable_io_add_ips_to_asset import TenableIoAddIPsToTargetGroup
from reports.action_types.base.tenable_sc_add_ips_to_asset import TenableScAddIPsToAsset
from reports.action_types.base.untag_all_entities import UntagAllEntitiesAction

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
    'create_service_now_incident': ServiceNowIncidentAction,
    'create_jira_incident': JiraIncidentAction,
    'enable_entities': EnableEntities,
    'disable_entities': DisableEntities,
    'create_sysaid_incident': SysaidIncidentAction,
    'slack_send_message': SlackSendMessageAction,
    'carbonblack_defense_change_policy': CarbonblackDefenseChangePolicyAction,
    'cybereason_isolate': CybereasonIsolateAction,
    'cybereason_unisolate': CybereasonUnisolateAction,
    'tenable_sc_add_ips_to_asset': TenableScAddIPsToAsset,
    'tenable_io_add_ips_to_target_group': TenableIoAddIPsToTargetGroup,
    'send_email_to_entities': SendEmailToEntities,
    'send_csv_to_share': SendCsvToShare,
    'send_csv_to_s3': SendCsvToS3,
    'run_wmi_scan': RunWMIScan,
    'run_linux_ssh_scan': RunLinuxSSHScan,
    'create_service_now_incident_per_entity': ServiceNowIncidentPerEntity,
}
