"""
Contains all the scored rules for the "Monitoring" Category of AWS CIS
"""
import logging
import re
from collections import defaultdict
from typing import Dict, List, Any

import boto3

from axonius.clients.aws.aws_clients import get_boto3_client_by_session
from compliance.aws_cis.account_report import AccountReport, RuleStatus
from compliance.aws_cis.aws_cis_utils import aws_cis_rule, \
    get_api_error, get_api_data, AWS_CIS_DEFAULT_REGION

logger = logging.getLogger(f'axonius.{__name__}')


class CISAWSCategory3:
    def __init__(self, report: AccountReport, session: boto3.Session, account_dict: dict, cloudtrails: Dict[str, list]):
        self.report = report
        self.session = session
        self.https_proxy = account_dict.get('https_proxy')
        self.region_name = account_dict.get('region_name') or AWS_CIS_DEFAULT_REGION
        self.cloudtrails = cloudtrails

        self.__services_by_regions = defaultdict(dict)

    def __get_service_for_region(self, service, region) -> Any:
        """
        Try to minimize the amount of times we create clients.
        """
        try:
            return self.__services_by_regions[region][service]
        except Exception:
            self.__services_by_regions[region][service] = get_boto3_client_by_session(
                service,
                self.session,
                region,
                self.https_proxy
            )

        return self.__services_by_regions[region][service]

    @staticmethod
    def __verify_all_re_in_string(string: str, regex_list: List[str]) -> bool:
        for regex in regex_list:
            if not re.search(regex, string):
                return False
        return True

    # pylint: disable=too-many-locals, too-many-nested-blocks, too-many-return-statements, too-many-branches
    def __check_cis_aws_generic(self, rule_section: str, patterns: List[str]):
        error = get_api_error(self.cloudtrails)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.cloudtrails)
        for region_name, cloudtrails_per_region in data.items():
            for cloudtrail in cloudtrails_per_region:
                # Verify this is a valid cloudtrail (multiregion, islogging enabled, and has IncludeManagementEvents
                # and ReadWriteType == 'All'

                if not cloudtrail.get('IsMultiRegionTrail'):
                    continue

                cloud_watch_logs_log_group_arn = cloudtrail.get('CloudWatchLogsLogGroupArn')
                if not cloud_watch_logs_log_group_arn:
                    continue

                cloudtrail_client = self.__get_service_for_region('cloudtrail', region_name)
                if not cloudtrail_client.get_trail_status(Name=cloudtrail.get('TrailARN')).get('IsLogging'):
                    continue

                event_selectors_response = cloudtrail_client.get_event_selectors(TrailName=cloudtrail.get('TrailARN'))

                is_valid_cloudtrail = False
                for ev_sel in (event_selectors_response.get('EventSelectors') or []):
                    if ev_sel.get('IncludeManagementEvents') and str(ev_sel.get('ReadWriteType', '')).lower() == 'all':
                        is_valid_cloudtrail = True
                        break

                if not is_valid_cloudtrail:
                    continue

                # Search for the metrics
                try:
                    group_name = re.search('log-group:(.+?):', cloud_watch_logs_log_group_arn).group(1)
                except Exception:
                    continue

                try:
                    logs_client = self.__get_service_for_region('logs', region_name)
                except Exception as e:
                    self.report.add_rule_error(
                        rule_section,
                        f'Could not establish connection to AWS Logs service: {str(e)}'
                    )
                    return

                # Describe all metric filters for that group name

                try:
                    metric_filters_response = logs_client.describe_metric_filters(
                        logGroupName=group_name
                    )
                except Exception as e:
                    self.report.add_rule_error(
                        rule_section,
                        f'Error using logs.describe_metric_filters: {str(e)}'
                    )
                    return

                # in each metric filter, check if the filter pattern contains all of our requirements
                # (passed in patterns)

                for metric_filter in (metric_filters_response.get('metricFilters') or []):
                    if self.__verify_all_re_in_string(metric_filter.get('filterPattern', ''), patterns):
                        try:
                            cloudwatch_client = self.__get_service_for_region('cloudwatch', region_name)
                        except Exception as e:
                            self.report.add_rule_error(
                                rule_section,
                                f'Could not establish connection to AWS Cloudwatch service: {str(e)}'
                            )
                            return

                        try:
                            sns_client = self.__get_service_for_region('sns', region_name)
                        except Exception as e:
                            self.report.add_rule_error(
                                rule_section,
                                f'Could not establish connection to AWS SNS service: {str(e)}'
                            )
                            return

                        try:
                            # For this metric filter, Search for all alarms
                            for metric_transformation in (metric_filter.get('metricTransformations') or []):
                                alarms_for_metric_response = cloudwatch_client.describe_alarms_for_metric(
                                    MetricName=metric_transformation['metricName'],
                                    Namespace=metric_transformation['metricNamespace']
                                ).get('MetricAlarms') or []

                                # For each alarm, go through all actions. For every sns action, get the subscribers.
                                # If there is at least one subscriber, we are good.

                                for alarm in alarms_for_metric_response:
                                    for alarm_action in alarm.get('AlarmActions') or []:
                                        if alarm_action.startswith('arn:aws:sns'):
                                            if len(sns_client.list_subscriptions_by_topic(
                                                    TopicArn=alarm_action
                                            ).get('Subscriptions') or []) > 0:
                                                self.report.add_rule(
                                                    RuleStatus.Passed,
                                                    rule_section,
                                                    (0, 1),
                                                    0,
                                                    ''
                                                )
                                                return
                        except Exception as e:
                            self.report.add_rule_error(
                                rule_section,
                                f'Error describing cloudwatch alarms ('
                                f'cloudwatch.describe_alarms_for_metric, sns.list_subscriptions_by_topic): {str(e)}'
                            )
                            return

        # If we have reached here, that means, that we haven't found any CloudTrail which is multi-regional,
        # has logging enabled, has the IncludeManagementEvents set to True, has the ReadWriteType set to ALL,
        # and is connected to a CloudWatch log group, which has the metric filters that are requested, and for that
        # one that is requested, contains an alarm, that has an action which is an sns action, and that sns action
        # has at least one subscriber.
        self.report.add_rule(
            RuleStatus.Failed,
            rule_section,
            (1, 1),
            0,
            'Could not find a log metric filter and an alarm that satisfies the conditions.'
        )

    # pylint: disable=anomalous-backslash-in-string
    @aws_cis_rule('3.1')
    def check_cis_aws_3_1(self, **kwargs):
        """
        3.1 Ensure a log metric filter and alarm exist for unauthorized API calls (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.errorCode\s*=\s*\"?\*UnauthorizedOperation(\"|\)|\s)',
            '\$\.errorCode\s*=\s*\"?AccessDenied\*(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.2')
    def check_cis_aws_3_2(self, **kwargs):
        """
        3.2 Ensure a log metric filter and alarm exist for Management Console sign-in without MFA (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.eventName\s*=\s*\"?ConsoleLogin(\"|\)|\s)',
            '\$\.additionalEventData\.MFAUsed\s*\!=\s*\"?Yes'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.3')
    def check_cis_aws_3_3(self, **kwargs):
        """
        3.3 Ensure a log metric filter and alarm exist for usage of "root" account (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.userIdentity\.type\s*=\s*\"?Root',
            '\$\.userIdentity\.invokedBy\s*NOT\s*EXISTS',
            '\$\.eventType\s*\!=\s*\"?AwsServiceEvent(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.4')
    def check_cis_aws_3_4(self, **kwargs):
        """
        3.4 Ensure a log metric filter and alarm exist for IAM policy changes (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.eventName\s*=\s*\"?DeleteGroupPolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteRolePolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteUserPolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?PutGroupPolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?PutRolePolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?PutUserPolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?CreatePolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeletePolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?CreatePolicyVersion(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeletePolicyVersion(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?AttachRolePolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DetachRolePolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?AttachUserPolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DetachUserPolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?AttachGroupPolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DetachGroupPolicy(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.5')
    def check_cis_aws_3_5(self, **kwargs):
        """
        3.5 Ensure a log metric filter and alarm exist for CloudTrail configuration changes (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.eventName\s*=\s*\"?CreateTrail(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?UpdateTrail(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteTrail(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?StartLogging(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?StopLogging(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.6')
    def check_cis_aws_3_6(self, **kwargs):
        """
        3.6 Ensure a log metric filter and alarm exist for AWS Management Console authentication failures (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.eventName\s*=\s*\"?ConsoleLogin(\"|\)|\s)',
            '\$\.errorMessage\s*=\s*\"?Failed authentication(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.7')
    def check_cis_aws_3_7(self, **kwargs):
        """
        3.7 Ensure a log metric filter and alarm exist for disabling or scheduled deletion of
        customer created CMKs (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.eventSource\s*=\s*\"?kms\.amazonaws\.com(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DisableKey(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?ScheduleKeyDeletion(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.8')
    def check_cis_aws_3_8(self, **kwargs):
        """
        3.8 Ensure a log metric filter and alarm exist for S3 bucket policy changes (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.eventSource\s*=\s*\"?s3\.amazonaws\.com(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?PutBucketAcl(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?PutBucketPolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?PutBucketCors(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?PutBucketLifecycle(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?PutBucketReplication(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteBucketPolicy(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteBucketCors(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteBucketLifecycle(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteBucketReplication(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.9')
    def check_cis_aws_3_9(self, **kwargs):
        """
        3.9 Ensure a log metric filter and alarm exist for AWS Config configuration changes (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.eventSource\s*=\s*\"?config\.amazonaws\.com(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?StopConfigurationRecorder(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteDeliveryChannel(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?PutDeliveryChannel(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?PutConfigurationRecorder(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.10')
    def check_cis_aws_3_10(self, **kwargs):
        """
        3.10 Ensure a log metric filter and alarm exist for security group changes (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.eventName\s*=\s*\"?AuthorizeSecurityGroupIngress(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?AuthorizeSecurityGroupEgress(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?RevokeSecurityGroupIngress(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?RevokeSecurityGroupEgress(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?CreateSecurityGroup(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteSecurityGroup(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.11')
    def check_cis_aws_3_11(self, **kwargs):
        """
        3.11 Ensure a log metric filter and alarm exist for changes to Network Access Control Lists (NACL) (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.eventName\s*=\s*\"?CreateNetworkAcl(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?CreateNetworkAclEntry(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteNetworkAcl(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteNetworkAclEntry(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?ReplaceNetworkAclEntry(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?ReplaceNetworkAclAssociation(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.12')
    def check_cis_aws_3_12(self, **kwargs):
        """
        3.12 Ensure a log metric filter and alarm exist for changes to network gateways (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.eventName\s*=\s*\"?CreateCustomerGateway(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteCustomerGateway(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?AttachInternetGateway(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?CreateInternetGateway(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteInternetGateway(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DetachInternetGateway(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.13')
    def check_cis_aws_3_13(self, **kwargs):
        """
        3.13 Ensure a log metric filter and alarm exist for route table changes (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.eventName\s*=\s*\"?CreateRoute(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?CreateRouteTable(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?ReplaceRoute(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?ReplaceRouteTableAssociation(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteRouteTable(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteRoute(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DisassociateRouteTable(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)

    @aws_cis_rule('3.14')
    def check_cis_aws_3_14(self, **kwargs):
        """
        3.14 Ensure a log metric filter and alarm exist for VPC changes (Scored)
        """
        rule_section = kwargs['rule_section']
        patterns = [
            '\$\.eventName\s*=\s*\"?CreateVpc(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteVpc(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?ModifyVpcAttribute(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?AcceptVpcPeeringConnection(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?CreateVpcPeeringConnection(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DeleteVpcPeeringConnection(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?RejectVpcPeeringConnection(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?AttachClassicLinkVpc(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DetachClassicLinkVpc(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?DisableVpcClassicLink(\"|\)|\s)',
            '\$\.eventName\s*=\s*\"?EnableVpcClassicLink(\"|\)|\s)'
        ]
        self.__check_cis_aws_generic(rule_section, patterns)
