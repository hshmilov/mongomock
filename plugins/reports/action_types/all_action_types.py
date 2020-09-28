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
from reports.action_types.alert.send_to_webhook import SendWebhookAction
from reports.action_types.alert.send_slack_message import SlackSendMessageAction
from reports.action_types.alert.send_syslog import NotifySyslogAction
from reports.action_types.base.create_ivanti_sm_computer import IvantiSmComputerAction
from reports.action_types.base.update_ivanti_sm_computer import UpdateIvantiSmComputerAction
from reports.action_types.base.aws_ec2_add_tags import AwsEc2AddTagsAction
from reports.action_types.base.aws_ec2_delete_tags import AwsEc2DeleteTagsAction
from reports.action_types.base.azure_add_tags import AzureAddTagsAction
from reports.action_types.base.carbonblack_defense_change_policy import CarbonblackDefenseChangePolicyAction
from reports.action_types.base.carbonblack_isolate import CarbonblackIsolateAction
from reports.action_types.base.carbonblack_unisolate import CarbonblackUnisolateAction
from reports.action_types.base.create_servicenow_computer import ServiceNowComputerAction
from reports.action_types.base.create_servicenow_incident_per_entity import ServiceNowIncidentPerEntity
from reports.action_types.base.cybereason_isolate import CybereasonIsolateAction
from reports.action_types.base.limacharlie_isolate import LimacharlieIsolateAction
from reports.action_types.base.limacharlie_unisolate import LimacharlieUnisolateAction
from reports.action_types.base.cybereason_unisolate import CybereasonUnisolateAction
from reports.action_types.base.disable_entity import DisableEntities
from reports.action_types.base.enable_entity import EnableEntities
from reports.action_types.base.run_cmd import RunCmd
from reports.action_types.base.run_linux_ssh_scan import RunLinuxSSHScan
from reports.action_types.base.shodan_enrichment import ShodanEnrichment
from reports.action_types.base.censys_enrichment import CensysEnrichment
from reports.action_types.base.run_wmi_scan import RunWMIScan
from reports.action_types.base.refetch_device import RefetchAction
from reports.action_types.alert.create_opsgenie_alert import OpsgenieCreateAlert
from reports.action_types.base.ldap_attributes import ChangeLdapAttribute
from reports.action_types.base.send_email_to_entities import SendEmailToEntities
from reports.action_types.base.tag_all_entities import TagAllEntitiesAction
from reports.action_types.base.add_custom_data import AddCustomDataAction
from reports.action_types.base.tenable_io_add_ips_to_asset import TenableIoAddIPsToTargetGroup
from reports.action_types.base.tenable_sc_add_ips_to_asset import TenableScAddIPsToAsset
from reports.action_types.base.untag_all_entities import UntagAllEntitiesAction
from reports.action_types.base.sentinelone_initiate_scan import SentineloneInitiateScanAction
from reports.action_types.base.haveibeenpwned_enrichment import HaveibeenpwnedEnrichment
from reports.action_types.alert.send_csv_to_scp import SendCsvToScp
from reports.action_types.base.run_linux_command import RunLinuxCommand
from reports.action_types.alert.create_cherwell_incident import CherwellIncidentAction
from reports.action_types.base.tenable_io_create_asset import TenableIoCreateAsset
from reports.action_types.base.cybereason_tags import CybereasonTagAction
from reports.action_types.alert.create_zendesk_ticket import ZendeskTicketAction
from reports.action_types.alert.create_remedy_ticket import RemedyTicketAction
from reports.action_types.base.portnox_enrichment import PortnoxEnrichment
from reports.action_types.alert.create_fresh_service_incident import FreshServiceIncidentAction
from reports.action_types.base.webscan_enrichment import WebscanEnrichment
from reports.action_types.base.update_service_now_computer import UpdateServicenowComputerAction
from reports.action_types.base.create_jira_ticket_per_entity import JiraIncidentPerEntityAction
from reports.action_types.base.automox_install_update import AutomoxInstallUpdateAction
from reports.action_types.base.carbonblack_defense_quarantine import CarbonblackDefenseQuarantineAction
from reports.action_types.base.carbonblack_defense_unquarantine import CarbonblackDefenseUnquarantineAction
from reports.action_types.base.qualys_create_asset import QualysCreateAsset
from reports.action_types.base.aws_ec2_start_instance import AwsEc2StartInstanceAction
from reports.action_types.base.tenable_io_ips_scans import TenableIoAddIPsToScan
from reports.action_types.base.aws_ec2_stop_instance import AwsEc2StopInstanceAction
from reports.action_types.base.desktop_central_do_som_action import DesktopCentralSomAction
from reports.action_types.base.qualys_add_tag import QualysAddTag
from reports.action_types.base.qualys_remove_tag import QualysRemoveTag
from reports.action_types.base.create_cherwell_computer import CherwellCreateComputerAction
from reports.action_types.base.update_cherwell_computer import CherwellUpdateComputerAction
from reports.action_types.base.rapid7_ips_to_site import Rapid7AddIPsToSite
from reports.action_types.base.create_jira_asset import CreateJiraAssetAction
from reports.action_types.alert.send_json_to_s3 import SendJsonToS3

AllActionTypes: Dict[str, type(ActionTypeBase)] = {
    'update_cherwell_computer': CherwellUpdateComputerAction,
    'rapid7_ips_to_site': Rapid7AddIPsToSite,
    'create_cherwell_computer': CherwellCreateComputerAction,
    'create_service_now_computer': ServiceNowComputerAction,
    'tag': TagAllEntitiesAction,
    'tenable_io_ips_scans': TenableIoAddIPsToScan,
    'desktop_central_do_som_action': DesktopCentralSomAction,
    'create_cherwell_incident': CherwellIncidentAction,
    'add_custom_data': AddCustomDataAction,
    'carbonblack_isolate': CarbonblackIsolateAction,
    'update_service_now_computer': UpdateServicenowComputerAction,
    'carbonblack_unisolate': CarbonblackUnisolateAction,
    'untag': UntagAllEntitiesAction,
    'run_command_windows': RunCmd,
    'create_notification': SystemNotificationAction,
    'send_emails': SendEmailsAction,
    'notify_syslog': NotifySyslogAction,
    'send_https_log': SendHttpsLogAction,
    'send_to_webhook': SendWebhookAction,
    'create_service_now_incident': ServiceNowIncidentAction,
    'create_jira_incident': JiraIncidentAction,
    'enable_entities': EnableEntities,
    'disable_entities': DisableEntities,
    'create_ivanti_sm_computer': IvantiSmComputerAction,
    'update_ivanti_sm_computer': UpdateIvantiSmComputerAction,
    'create_sysaid_incident': SysaidIncidentAction,
    'slack_send_message': SlackSendMessageAction,
    'carbonblack_defense_change_policy': CarbonblackDefenseChangePolicyAction,
    'cybereason_isolate': CybereasonIsolateAction,
    'limacharlie_isolate': LimacharlieIsolateAction,
    'cybereason_unisolate': CybereasonUnisolateAction,
    'limacharlie_unisolate': LimacharlieUnisolateAction,
    'cybereason_tag': CybereasonTagAction,
    'tenable_sc_add_ips_to_asset': TenableScAddIPsToAsset,
    'tenable_io_add_ips_to_target_group': TenableIoAddIPsToTargetGroup,
    'send_email_to_entities': SendEmailToEntities,
    'send_csv_to_share': SendCsvToShare,
    'send_csv_to_s3': SendCsvToS3,
    'run_wmi_scan': RunWMIScan,
    'refetch_action': RefetchAction,
    'run_linux_ssh_scan': RunLinuxSSHScan,
    'change_ldap_attribute': ChangeLdapAttribute,
    'shodan_enrichment': ShodanEnrichment,
    'censys_enrichment': CensysEnrichment,
    'create_service_now_incident_per_entity': ServiceNowIncidentPerEntity,
    'sentinelone_initiate_scan_action': SentineloneInitiateScanAction,
    'haveibeenpwned_enrichment': HaveibeenpwnedEnrichment,
    'run_command_linux': RunLinuxCommand,
    'tenable_io_create_asset': TenableIoCreateAsset,
    'create_zendesk_ticket': ZendeskTicketAction,
    'create_remedy_ticket': RemedyTicketAction,
    'portnox_enrichment': PortnoxEnrichment,
    'create_fresh_service_incident': FreshServiceIncidentAction,
    'webscan_enrichment': WebscanEnrichment,
    'jira_incident_per_entity_action': JiraIncidentPerEntityAction,
    'jira_create_asset': CreateJiraAssetAction,
    'automox_install_update': AutomoxInstallUpdateAction,
    'carbonblack_defense_quarantine': CarbonblackDefenseQuarantineAction,
    'carbonblack_defense_unquarantine': CarbonblackDefenseUnquarantineAction,
    'qualys_create_asset': QualysCreateAsset,
    'aws_ec2_start_instance': AwsEc2StartInstanceAction,
    'aws_ec2_stop_instance': AwsEc2StopInstanceAction,
    'aws_ec2_add_tags': AwsEc2AddTagsAction,
    'aws_ec2_delete_tags': AwsEc2DeleteTagsAction,
    'azure_add_tags': AzureAddTagsAction,
    'send_csv_to_scp': SendCsvToScp,
    'qualys_add_tag': QualysAddTag,
    'qualys_remove_tag': QualysRemoveTag,
    'opsgenie_create_alert': OpsgenieCreateAlert,
    'send_json_to_s3': SendJsonToS3,
}
