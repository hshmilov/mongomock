"""
AWS Cis helpers
"""
# pylint: disable=too-many-branches
import datetime
import logging
from typing import List

from aws_adapter.connection.structures import AWSUserAdapter, AWSDeviceAdapter, AWSSecurityGroup, AWSIAMAccessKey, \
    AWSIAMPolicy

logger = logging.getLogger(f'axonius.{__name__}')


def append_aws_cis_data_to_device(device: AWSDeviceAdapter):
    device_type = device.get_field_safe('aws_device_type')

    if device_type == 'S3':
        if device.get_field_safe('s3_bucket_used_for_cloudtrail'):
            if not device.get_field_safe('s3_bucket_logging_target'):
                device.add_aws_cis_incompliant_rule('2.6')
            if device.get_field_safe('s3_bucket_is_public'):
                device.add_aws_cis_incompliant_rule('2.3')

    all_security_groups: List[AWSSecurityGroup] = device.get_field_safe('security_groups') or []

    for security_group in all_security_groups:
        security_group_name = security_group.get_field_safe('name')
        security_group_inbound = security_group.get_field_safe('inbound') or []
        security_group_outbound = security_group.get_field_safe('outbound') or []

        if security_group_name == 'default' and (len(security_group_inbound) + len(security_group_outbound)) != 0:
            device.add_aws_cis_incompliant_rule('4.3')

        for inbound_rule in security_group_inbound:
            ip_ranges = inbound_rule.get_field_safe('ip_ranges') or []
            from_port = inbound_rule.get_field_safe('from_port')
            to_port = inbound_rule.get_field_safe('to_port')
            ip_protocol = inbound_rule.get_field_safe('ip_protocol')

            if '0.0.0.0/0' in str(ip_ranges):
                if str(ip_protocol) in ['-1', 'Any']:
                    device.add_aws_cis_incompliant_rule('4.1')
                    device.add_aws_cis_incompliant_rule('4.2')
                elif from_port and to_port and from_port <= 22 <= to_port:
                    device.add_aws_cis_incompliant_rule('4.1')
                elif from_port and to_port and from_port <= 3389 <= to_port:
                    device.add_aws_cis_incompliant_rule('4.2')


def append_aws_cis_data_to_user(user: AWSUserAdapter):
    username: str = user.get_field_safe('username')
    a_month_ago: datetime.datetime = datetime.datetime.utcnow().astimezone(
        datetime.timezone.utc) - datetime.timedelta(days=30)
    a_3_months_ago: datetime.datetime = datetime.datetime.utcnow().astimezone(
        datetime.timezone.utc) - datetime.timedelta(days=90)
    password_last_used: datetime.datetime = user.get_field_safe('user_pass_last_used')
    access_keys: List[AWSIAMAccessKey] = user.get_field_safe('user_attached_keys') or []
    is_password_enabled = user.get_field_safe('user_is_password_enabled')

    if username.endswith(':root'):
        if password_last_used and password_last_used > a_month_ago:
            user.add_aws_cis_incompliant_rule('1.1')
        else:
            for access_key in access_keys:
                access_key_last_used_time = access_key.get_field_safe('last_used_time')
                if access_key_last_used_time and access_key_last_used_time > a_month_ago:
                    user.add_aws_cis_incompliant_rule('1.1')
                    break

        for access_key in access_keys:
            if access_key.get_field_safe('status') == 'Active':
                user.add_aws_cis_incompliant_rule('1.12')
                break

        if user.get_field_safe('has_associated_mfa_devices') is True:
            user.add_aws_cis_incompliant_rule('1.13')

        if user.get_field_safe('uses_virtual_mfa') is True:
            user.add_aws_cis_incompliant_rule('1.14')

    if is_password_enabled is True and not user.get_field_safe('has_associated_mfa_devices'):
        user.add_aws_cis_incompliant_rule('1.2')

    if is_password_enabled is True and password_last_used and password_last_used < a_3_months_ago:
        user.add_aws_cis_incompliant_rule('1.3')
    else:
        for access_key in access_keys:
            access_key_last_used_time = access_key.get_field_safe('last_used_time')
            if access_key.get_field_safe('status') == 'Active' and \
                    access_key_last_used_time and access_key_last_used_time < a_3_months_ago:
                user.add_aws_cis_incompliant_rule('1.3')
                break

    for access_key in access_keys:
        access_key_last_rotated = access_key.get_field_safe('create_date')
        if access_key.get_field_safe('status') == 'Active' and \
                access_key_last_rotated and access_key_last_rotated < a_3_months_ago:
            user.add_aws_cis_incompliant_rule('1.4')
            break

    user_attached_policies: List[AWSIAMPolicy] = user.get_field_safe('user_attached_policies') or []
    for user_attached_policy in user_attached_policies:
        if user_attached_policy.get_field_safe('policy_type') in ['Managed', 'Inline']:
            user.add_aws_cis_incompliant_rule('1.16')
            break
