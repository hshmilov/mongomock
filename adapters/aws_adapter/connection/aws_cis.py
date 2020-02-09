"""
AWS Cis helpers
"""
import logging
from typing import List

from aws_adapter.connection.structures import AWSUserAdapter, AWSDeviceAdapter, AWSSecurityGroup


logger = logging.getLogger(f'axonius.{__name__}')


def append_aws_cis_data_to_device(device: AWSDeviceAdapter):
    device.aws_cis_incompliant = []

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
    user.aws_cis_incompliant = []
