"""
Contains all the scored rules for the "Networking" Category of AWS CIS
"""
import logging
from typing import List

import boto3

from axonius.clients.aws.aws_clients import get_boto3_client_by_session
from axonius.clients.aws.consts import REGIONS_NAMES
from axonius.entities import EntityType
from compliance.utils.account_report import AccountReport, RuleStatus
from compliance.aws_cis.aws_cis_utils import aws_cis_rule, bad_api_response, good_api_response, \
    get_api_error, get_api_data, get_count_incompliant_cis_rule, errors_to_gui

logger = logging.getLogger(f'axonius.{__name__}')


def get_security_groups(session: boto3.Session, regions: List[str], https_proxy: str):
    try:
        all_security_groups = []
        first_exception = None
        for region_name in regions:
            try:
                logger.debug(f'Getting security groups for region {region_name}..')
                ec2_client = get_boto3_client_by_session('ec2', session, region_name, https_proxy)

                for security_groups_page in ec2_client.get_paginator('describe_security_groups').paginate():
                    for security_group in (security_groups_page.get('SecurityGroups') or []):
                        security_group['region_name'] = region_name
                        all_security_groups.append(security_group)
            except Exception as e:
                logger.debug(f'Exception while getting security groups for region {region_name}', exc_info=True)
                if not first_exception:
                    first_exception = e

        if not all_security_groups:
            raise first_exception
        return good_api_response(all_security_groups)
    except Exception as e:
        logger.debug(f'Exception while describing security groups', exc_info=True)
        return bad_api_response(
            f'Error describing security groups (ec2.describe_security_groups) - {str(e)}'
        )


class CISAWSCategory4:
    def __init__(self, report: AccountReport, session: boto3.Session, account_dict: dict):
        self.report = report

        if account_dict.get('region_name') and not account_dict.get('get_all_regions'):
            regions = [account_dict.get('region_name')]
        else:
            regions = REGIONS_NAMES

        self.security_groups = get_security_groups(session, regions, account_dict.get('https_proxy'))
        self.account_id = account_dict.get('account_id_number')

    @aws_cis_rule('4.1')
    def check_cis_aws_4_1(self, **kwargs):
        """
        4.1 Ensure no security groups allow ingress from 0.0.0.0/0 to port 22 (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.security_groups)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.security_groups)
        bad_security_groups = []
        for security_group in data:
            if '0.0.0.0/0' in str(security_group['IpPermissions']):
                for inbound_rules in security_group['IpPermissions']:
                    try:
                        if int(inbound_rules['FromPort']) <= 22 <= int(inbound_rules['ToPort']) \
                                and '0.0.0.0/0' in str(inbound_rules['IpRanges']):
                            bad_security_groups.append(f'Security group "{security_group["GroupName"]}" '
                                                       f'({security_group["GroupId"]}) in region '
                                                       f'{security_group["region_name"]} allow ingress '
                                                       f'access to port 22 to the whole world')
                    except Exception:
                        if str(inbound_rules['IpProtocol']) == '-1' and '0.0.0.0/0' in str(inbound_rules['IpRanges']):
                            bad_security_groups.append(f'Security group "{security_group["GroupName"]}" '
                                                       f'({security_group["GroupId"]}) in region '
                                                       f'{security_group["region_name"]} allow ingress '
                                                       f'access in all ports to the whole world')

        if bad_security_groups:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(bad_security_groups), len(data)),
                get_count_incompliant_cis_rule(EntityType.Devices, self.account_id, rule_section),
                errors_to_gui(bad_security_groups),
                {
                    'type': 'devices',
                    'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                             f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                             f'(data.aws_account_id == "{self.account_id or ""}")])'
                }
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, len(data)),
                0,
                ''
            )

    @aws_cis_rule('4.2')
    def check_cis_aws_4_2(self, **kwargs):
        """
        4.2 Ensure no security groups allow ingress from 0.0.0.0/0 to port 3389 (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.security_groups)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.security_groups)
        bad_security_groups = []
        for security_group in data:
            if '0.0.0.0/0' in str(security_group['IpPermissions']):
                for inbound_rules in security_group['IpPermissions']:
                    try:
                        if int(inbound_rules['FromPort']) <= 3389 <= int(inbound_rules['ToPort']) \
                                and '0.0.0.0/0' in str(inbound_rules['IpRanges']):
                            bad_security_groups.append(f'Security group "{security_group["GroupName"]}" '
                                                       f'({security_group["GroupId"]}) in region '
                                                       f'{security_group["region_name"]} opens port 3389 to the world')
                    except Exception:
                        if str(inbound_rules['IpProtocol']) == '-1' and '0.0.0.0/0' in str(inbound_rules['IpRanges']):
                            bad_security_groups.append(f'Security group "{security_group["GroupName"]}" '
                                                       f'({security_group["GroupId"]}) in region '
                                                       f'{security_group["region_name"]} opens all ports to the world')

        if bad_security_groups:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(bad_security_groups), len(data)),
                get_count_incompliant_cis_rule(EntityType.Devices, self.account_id, rule_section),
                errors_to_gui(bad_security_groups),
                {
                    'type': 'devices',
                    'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                             f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                             f'(data.aws_account_id == "{self.account_id or ""}")])'
                }
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, len(data)),
                0,
                ''
            )

    @aws_cis_rule('4.3')
    def check_cis_aws_4_3(self, **kwargs):
        """
        4.3 Ensure the default security group of every VPC restricts all traffic (Scored)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self.security_groups)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        data = get_api_data(self.security_groups)
        all_default_security_groups = []
        for security_group in data:
            if security_group.get('GroupName') == 'default':
                all_default_security_groups.append(security_group)

        bad_default_security_groups = []
        for security_group in all_default_security_groups:
            inbound_permissions = security_group.get('IpPermissions') or []
            outbount_permissions = security_group.get('IpPermissionsEgress') or []
            if not (len(inbound_permissions) + len(outbount_permissions)) == 0:
                bad_default_security_groups.append(
                    f'Default security group "{security_group["GroupName"]}" '
                    f'({security_group["GroupId"]}) in region '
                    f'{security_group["region_name"]} does not restrict access to all traffic')

        if bad_default_security_groups:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(bad_default_security_groups), len(all_default_security_groups)),
                get_count_incompliant_cis_rule(EntityType.Devices, self.account_id, rule_section),
                errors_to_gui(bad_default_security_groups),
                {
                    'type': 'devices',
                    'query': f'specific_data == match([plugin_name == \'aws_adapter\' and '
                             f'(data.aws_cis_incompliant.rule_section == "{rule_section}") and '
                             f'(data.aws_account_id == "{self.account_id or ""}")])'
                }
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, len(all_default_security_groups)),
                0,
                ''
            )
