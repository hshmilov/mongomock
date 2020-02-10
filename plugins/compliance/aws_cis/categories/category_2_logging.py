"""
Contains all the scored rules for the "Logging" Category of AWS CIS
"""
# pylint: disable=too-many-branches, too-many-nested-blocks
import datetime
import json
import logging
import re
from collections import defaultdict
from typing import Dict

import boto3

from axonius.clients.aws.aws_clients import get_boto3_client_by_session
from axonius.clients.aws.consts import REGIONS_NAMES
from axonius.utils.datetime import parse_date
from compliance.aws_cis.account_report import AccountReport, RuleStatus
from compliance.aws_cis.aws_cis_utils import aws_cis_rule, \
    get_api_error, get_api_data, AWS_CIS_DEFAULT_REGION, errors_to_gui

logger = logging.getLogger(f'axonius.{__name__}')


class CISAWSCategory2:
    def __init__(self, report: AccountReport, session: boto3.Session, account_dict: dict, cloudtrails: Dict[str, list]):
        self.report = report
        self.session = session
        self.https_proxy = account_dict.get('https_proxy')
        self.account_id = account_dict.get('account_id_number')
        self.region_name = AWS_CIS_DEFAULT_REGION if account_dict.get('get_all_regions') \
            else account_dict.get('region_name')
        self.cloudtrails = cloudtrails

        if account_dict.get('region_name') and not account_dict.get('get_all_regions'):
            self.all_regions = [account_dict.get('region_name')]
        else:
            self.all_regions = REGIONS_NAMES

    @aws_cis_rule('2.1')
    def check_cis_aws_2_1(self, **kwargs):
        """
        2.1 Ensure CloudTrail is enabled in all regions (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.cloudtrails)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.cloudtrails)

        for region_name, cloudtrails_per_region in data.items():
            for cloudtrail in cloudtrails_per_region:
                if not cloudtrail.get('IsMultiRegionTrail'):
                    continue
                cloudtrail_client = get_boto3_client_by_session(
                    'cloudtrail', self.session, region_name, self.https_proxy
                )

                response = cloudtrail_client.get_trail_status(Name=cloudtrail.get('TrailARN'))
                if not response.get('IsLogging'):
                    continue
                response = cloudtrail_client.get_event_selectors(TrailName=cloudtrail.get('TrailARN'))
                for ev_sel in (response.get('EventSelectors') or []):
                    if ev_sel.get('IncludeManagementEvents') and str(ev_sel.get('ReadWriteType', '').lower()) == 'all':
                        self.report.add_rule(
                            RuleStatus.Passed,
                            rule_section,
                            (0, 1),
                            0,
                            ''
                        )
                        return

        # If we have gotten here then we have not found any multi-regional enabled trail which has managementevents
        # and readwritetype in ALL.
        self.report.add_rule(
            RuleStatus.Failed,
            rule_section,
            (1, 1),
            0,
            'Could not find a multi-regional trail that has logging enabled, includes management events, and has '
            'ReadWriteType set to All.'
        )

    @aws_cis_rule('2.2')
    def check_cis_aws_2_2(self, **kwargs):
        """
        2.2 Ensure CloudTrail log file validation is enabled (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.cloudtrails)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.cloudtrails)
        errors = []
        num_of_cloudtrails = 0
        for region_name, cloudtrails in data.items():
            for cloudtrail in cloudtrails:
                num_of_cloudtrails += 1
                if not cloudtrail.get('LogFileValidationEnabled'):
                    errors.append(f'CloudTrail {cloudtrail.get("Name")} ({cloudtrail.get("TrailARN")}) '
                                  f'has no log file validation enabled.')

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), num_of_cloudtrails),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, num_of_cloudtrails),
                0,
                ''
            )

    @aws_cis_rule('2.3')
    def check_cis_aws_2_3(self, **kwargs):
        """
        2.3 Ensure the S3 bucket used to store CloudTrail logs is not publicly accessible (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.cloudtrails)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        try:
            s3_client = get_boto3_client_by_session('s3', self.session, self.region_name, self.https_proxy)
        except Exception as e:
            self.report.add_rule_error(rule_section, f'Could not create s3 connection: {str(e)}')
            return

        data = get_api_data(self.cloudtrails)
        errors = []
        num_of_cloudtrails = 0
        for region_name, cloudtrails in data.items():
            for cloudtrail in cloudtrails:
                num_of_cloudtrails += 1
                s3_bucket_name = cloudtrail.get('S3BucketName')
                if not s3_bucket_name:
                    continue

                try:
                    bucket_acl = s3_client.get_bucket_acl(Bucket=s3_bucket_name)
                    bucket_policy = s3_client.get_bucket_policy(Bucket=s3_bucket_name).get('Policy')
                except Exception as e:
                    errors.append(f'CloudTrail "{cloudtrail.get("Name")}" ({cloudtrail.get("TrailARN")}): '
                                  f'Could not verify Bucket Permissions for bucket {s3_bucket_name} '
                                  f'(using s3.get_bucket_acl and s3.get_bucket_policy): {str(e)}')
                    continue

                # Check ACL
                bucket_public = False
                for grant_statement in bucket_acl.get('Grants'):
                    if re.search(r'(global/AllUsers|global/AuthenticatedUsers)', str(grant_statement['Grantee'])):
                        bucket_public = True
                        break

                if bucket_public:
                    errors.append(f'CloudTrail "{cloudtrail.get("Name")}" ({cloudtrail.get("TrailARN")}): '
                                  f'bucket {s3_bucket_name} is public: ACL allows AllUsers/AuthenticatedUsers')
                    continue

                # Check Policy
                if bucket_policy:
                    try:
                        bucket_policy = json.loads(bucket_policy)
                        for statement in (bucket_policy.get('Statement') or []):
                            principal = str(statement.get('Principal'))
                            if statement.get('Effect') == 'Allow' and principal in ['*', '{"AWS": "*"}']:
                                bucket_public = True
                                break
                    except Exception as e:
                        errors.append(f'CloudTrail "{cloudtrail.get("Name")}" ({cloudtrail.get("TrailARN")}): '
                                      f'Could not verify Bucket Policy for bucket {s3_bucket_name} : {str(e)}')

                if bucket_public:
                    errors.append(f'CloudTrail "{cloudtrail.get("Name")}" ({cloudtrail.get("TrailARN")}): '
                                  f'bucket {s3_bucket_name} is public: Policy contains "Allow *" statement')
                continue

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), num_of_cloudtrails),
                len(errors),
                errors_to_gui(errors),
                {
                    'type': 'devices',
                    'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                             f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                             f'(data.aws_account_id == {self.account_id or 0})])'
                }
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, num_of_cloudtrails),
                0,
                ''
            )

    @aws_cis_rule('2.4')
    def check_cis_aws_2_4(self, **kwargs):
        """
        2.4 Ensure CloudTrail trails are integrated with CloudWatch Logs (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.cloudtrails)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.cloudtrails)
        errors = []
        num_of_cloudtrails = 0
        for region_name, cloudtrails in data.items():
            cloudtrail_client = get_boto3_client_by_session(
                'cloudtrail', self.session, region_name, self.https_proxy
            )

            for cloudtrail in cloudtrails:
                num_of_cloudtrails += 1
                if 'arn:aws:logs' not in cloudtrail.get('CloudWatchLogsLogGroupArn', ''):
                    errors.append(f'CloudTrail "{cloudtrail.get("Name")}" ({cloudtrail.get("TrailARN")}): '
                                  f'not integrated with CloudWatch Logs')
                    continue

                response = cloudtrail_client.get_trail_status(Name=cloudtrail.get('TrailARN'))
                latest_delivery_time = parse_date(response.get('LatestcloudwatchLogdDeliveryTime'))
                a_day_ago = datetime.datetime.utcnow().astimezone(datetime.timezone.utc) - datetime.timedelta(days=1)
                if not latest_delivery_time:
                    errors.append(f'CloudTrail "{cloudtrail.get("Name")}" ({cloudtrail.get("TrailARN")}): '
                                  f'Latest Delivery time does not exist')
                elif latest_delivery_time and latest_delivery_time < a_day_ago:
                    errors.append(f'CloudTrail "{cloudtrail.get("Name")}" ({cloudtrail.get("TrailARN")}): '
                                  f'Latest Delivery time is too old: {latest_delivery_time}')
                    continue

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), num_of_cloudtrails),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, num_of_cloudtrails),
                0,
                ''
            )

    @aws_cis_rule('2.5')
    def check_cis_aws_2_5(self, **kwargs):
        """
        2.5 Ensure AWS Config is enabled in all regions (Scored)
        """
        rule_section = kwargs['rule_section']

        errors = []
        num_of_read_regions = 0
        first_exception = None
        for region_name in self.all_regions:
            try:
                try:
                    configuration_recorders_by_name = dict()
                    configuration_recorders_status_by_name = dict()
                    config_client = get_boto3_client_by_session('config', self.session, region_name, self.https_proxy)

                    for conrec in (config_client.describe_configuration_recorders().get(
                            'ConfigurationRecorders') or []):
                        if 'name' not in conrec:
                            continue
                        configuration_recorders_by_name[conrec['name']] = conrec

                    for conrec_status in (config_client.describe_configuration_recorder_status().get(
                            'ConfigurationRecordersStatus') or []):
                        if 'name' not in conrec_status:
                            continue
                        configuration_recorders_status_by_name[conrec_status['name']] = conrec_status

                except Exception as e:
                    raise ValueError(
                        f'Error describing configuration recorders for region {region_name} '
                        f'(config.describe_configuration_recorders, config.describe_configuration_recorder_status): '
                        f'{str(e)}')

                did_find_valid_config_recorder = False
                for configuration_recorder_name, configuration_recorder in configuration_recorders_by_name.items():
                    recording_group = configuration_recorder.get('recordingGroup') or {}
                    if recording_group.get('allSupported') and recording_group.get('includeGlobalResourceTypes'):
                        config_recorder_status = configuration_recorders_status_by_name.get(configuration_recorder_name)
                        if config_recorder_status.get('recording') and str(
                                config_recorder_status.get('lastStatus', '')).lower() == 'success':
                            did_find_valid_config_recorder = True
                            break

                if not did_find_valid_config_recorder:
                    errors.append(f'AWS Config not enabled properly in region {region_name}: Did not '
                                  f'find valid configuration recorder')
                num_of_read_regions += 1
            except Exception as e:
                if not first_exception:
                    first_exception = e
                logger.debug(f'2.5 Could not parse region {region_name}', exc_info=True)

        if not num_of_read_regions:
            self.report.add_rule_error(
                rule_section,
                str(first_exception)
            )
            return

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), num_of_read_regions),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, num_of_read_regions),
                0,
                ''
            )

    @aws_cis_rule('2.6')
    def check_cis_aws_2_6(self, **kwargs):
        """
        2.6 Ensure S3 bucket access logging is enabled on the CloudTrail S3 bucket (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.cloudtrails)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        try:
            s3_client = get_boto3_client_by_session('s3', self.session, self.region_name, self.https_proxy)
        except Exception as e:
            self.report.add_rule_error(rule_section, f'Could not create s3 connection: {str(e)}')
            return

        data = get_api_data(self.cloudtrails)
        errors = []
        num_of_cloudtrails = 0

        for region_name, cloudtrails in data.items():
            for cloudtrail in cloudtrails:
                num_of_cloudtrails += 1
                s3_bucket_name = cloudtrail.get('S3BucketName')
                if not s3_bucket_name:
                    continue

                try:
                    response = s3_client.get_bucket_logging(Bucket=s3_bucket_name)
                except Exception as e:
                    errors.append(f'CloudTrail "{cloudtrail.get("Name")}" ({cloudtrail.get("TrailARN")}): '
                                  f'Could not verify Bucket access logging for bucket {s3_bucket_name} '
                                  f'(using s3.get_bucket_logging): {str(e)}')
                    continue

                if 'LoggingEnabled' not in response:
                    errors.append(f'CloudTrail "{cloudtrail.get("Name")}" ({cloudtrail.get("TrailARN")}): '
                                  f'Bucket {s3_bucket_name} does not have bucket access logging enabled')
                    continue

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), num_of_cloudtrails),
                len(errors),
                errors_to_gui(errors),
                {
                    'type': 'devices',
                    'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                             f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                             f'(data.aws_account_id == {self.account_id or 0})])'
                }
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, num_of_cloudtrails),
                0,
                ''
            )

    @aws_cis_rule('2.7')
    def check_cis_aws_2_7(self, **kwargs):
        """
        2.7 Ensure CloudTrail logs are encrypted at rest using KMS CMKs (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.cloudtrails)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.cloudtrails)
        errors = []
        num_of_cloudtrails = 0

        for region_name, cloudtrails in data.items():
            for cloudtrail in cloudtrails:
                num_of_cloudtrails += 1

                if 'KmsKeyId' not in cloudtrail:
                    errors.append(f'CloudTrail "{cloudtrail.get("Name")}" ({cloudtrail.get("TrailARN")}) is not using '
                                  f'KMS CMK\'s')
                    continue

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), num_of_cloudtrails),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, num_of_cloudtrails),
                0,
                ''
            )

    @aws_cis_rule('2.8')
    def check_cis_aws_2_8(self, **kwargs):
        """
        2.8 Ensure rotation for customer created CMKs is enabled (Scored)
        """
        rule_section = kwargs['rule_section']
        keys_by_region = defaultdict(list)
        first_exception = None
        for region in self.all_regions:
            try:
                kms_client = get_boto3_client_by_session('kms', self.session, region, self.https_proxy)
                for result_page in kms_client.get_paginator('list_keys').paginate():
                    keys_by_region[region].extend(result_page.get('Keys') or [])
            except Exception as e:
                logger.debug(f'2.8 Could not parse region {region}', exc_info=True)
                if not first_exception:
                    first_exception = e

        if not keys_by_region.keys():
            self.report.add_rule_error(
                rule_section,
                f'Error listing KMS keys (kms.list_keys): {str(first_exception)}'
            )
            return

        num_of_keys = 0
        errors = []
        for region_name, keys in keys_by_region.items():
            for key in keys:
                num_of_keys += 1
                if not key.get('KeyRotationEnabled'):
                    errors.append(f'Rotation for key "{key.get("KeyArn")}" is not enabled.')

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), num_of_keys),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, num_of_keys),
                0,
                ''
            )

    @aws_cis_rule('2.9')
    def check_cis_aws_2_9(self, **kwargs):
        """
        2.9 Ensure VPC flow logging is enabled in all VPCs (Scored)
        """
        rule_section = kwargs['rule_section']
        vpcs_by_region = defaultdict(list)
        active_flow_logs_by_resource_id = defaultdict(list)
        first_exception = None
        did_one_succeed = False
        for region in self.all_regions:
            try:
                ec2_client = get_boto3_client_by_session('ec2', self.session, region, self.https_proxy)
                for result_page in ec2_client.get_paginator('describe_vpcs').paginate():
                    vpcs_by_region[region].extend(result_page.get('Vpcs') or [])

                for result_page in ec2_client.get_paginator('describe_flow_logs').paginate():
                    for flow_log in (result_page.get('FlowLogs') or []):
                        if 'ResourceId' not in flow_log:
                            continue
                        if str(flow_log.get('FlowLogStatus', '').lower()) != 'active':
                            continue
                        active_flow_logs_by_resource_id[flow_log['ResourceId']] = flow_log

                did_one_succeed = True
            except Exception as e:
                if not first_exception:
                    first_exception = e
                logger.debug(f'2.9 (Ensure VPC flow loging is enabled): Could not parse region {region}')

        if not did_one_succeed:
            self.report.add_rule_error(
                rule_section,
                f'Error checking VPC flow logs\'s (ec2.describe_vpcs, ec2.describe_flow_logs): {str(first_exception)}'
            )
            return

        errors = []
        num_of_vpcs = 0
        for region_name, vpcs in vpcs_by_region.items():
            for vpc in vpcs:
                num_of_vpcs += 1
                vpc_id = vpc.get('VpcId') or ''
                if not active_flow_logs_by_resource_id.get(vpc_id):
                    vpc_name = [tag['Value'] for tag in (vpc.get('Tags') or []) if tag['Key'] == 'Name']
                    vpc_name = f'"{vpc_name[0]}" ({vpc_id})' if vpc_name else str(vpc_id)

                    errors.append(f'VPC {vpc_name} in region {region_name} does not have active flow logs')

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), num_of_vpcs),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, num_of_vpcs),
                0,
                ''
            )
