import logging
from typing import List

import boto3
from botocore.waiter import WaiterModel, Waiter, WaiterError
from botocore.waiter import create_waiter_with_client

from aws_adapter.connection.structures import AWSS3PolicyStatement, AWSDeviceAdapter, AWSIPRule

logger = logging.getLogger(f'axonius.{__name__}')
PAGE_NUMBER_FLOOD_PROTECTION = 9000
BOTO3_FILTERS_LIMIT = 100


def get_paginated_next_token_api(func):
    next_token = None
    page_number = 0
    next_token_name = None

    while page_number < PAGE_NUMBER_FLOOD_PROTECTION:
        page_number += 1
        if next_token:
            result = func(**{next_token_name: next_token})
        else:
            result = func()

        yield result

        if result.get('nextToken'):
            next_token_name = 'nextToken'
        elif result.get('NextToken'):
            next_token_name = 'NextToken'

        if next_token_name:
            next_token = result.get(next_token_name)
        if not next_token:
            break

    if page_number == PAGE_NUMBER_FLOOD_PROTECTION:
        logger.critical('AWS Pagination: reached page flood protection count')


def get_paginated_marker_api(func):
    marker = None
    marker_name = None
    page_number = 0

    while page_number < PAGE_NUMBER_FLOOD_PROTECTION:
        page_number += 1
        if marker:
            result = func(**{marker_name: marker})
        else:
            result = func()

        yield result

        if result.get('Marker'):
            marker_name = 'Marker'
            marker = result.get('Marker')
        elif result.get('marker'):
            marker_name = 'marker'
            marker = result.get('marker')
        elif result.get('NextMarker'):
            # example
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference
            # /services/lambda.html#Lambda.Client.list_functions
            marker_name = 'Marker'
            marker = result.get('NextMarker')
        else:
            marker = None

        if not marker:
            # if marker is None or 0 or ''
            break

    if page_number == PAGE_NUMBER_FLOOD_PROTECTION:
        logger.critical('AWS Pagination: reached page flood protection count')


def parse_bucket_policy_statements(bucket_policy: dict) -> List[AWSS3PolicyStatement]:
    statements = []
    for statement_raw in (bucket_policy.get('Statement') or []):
        statement_action = statement_raw.get('Action')
        if isinstance(statement_action, str):
            statement_action = statement_action.split(',')
        elif not isinstance(statement_action, list):
            statement_action = [str(statement_action)]

        statements.append(AWSS3PolicyStatement(
            sid=statement_raw.get('Sid'),
            principal=statement_raw.get('Principal'),
            effect=statement_raw.get('Effect'),
            resource=statement_raw.get('Resource'),
            condition=statement_raw.get('Condition'),
            action=statement_action
        ))

    return statements or None


def make_ip_rules_list(ip_pemissions_list: list):
    ip_rules = []
    if not isinstance(ip_pemissions_list, list):
        return None
    for ip_pemission in ip_pemissions_list:
        if not isinstance(ip_pemission, dict):
            continue
        from_port = int(ip_pemission.get('FromPort')) \
            if ip_pemission.get('FromPort') is not None else None
        to_port = int(ip_pemission.get('ToPort')) \
            if ip_pemission.get('ToPort') is not None else None
        ip_protocol = str(ip_pemission.get('IpProtocol')) \
            if ip_pemission.get('IpProtocol') else None
        if ip_protocol == '-1':
            ip_protocol = 'Any'
        ip_ranges_raw = ip_pemission.get('IpRanges') or []
        ip_ranges_raw_v6 = ip_pemission.get('Ipv6Ranges') or []
        ip_ranges_raw += ip_ranges_raw_v6
        ip_ranges = []
        for ip_range_raw in ip_ranges_raw:
            ip_ranges.append((ip_range_raw.get('CidrIp') or '') +
                             (ip_range_raw.get('CidrIpv6') or '') +
                             '_Description:' + (ip_range_raw.get('Description') or ''))
        ip_rules.append(AWSIPRule(from_port=from_port,
                                  to_port=to_port,
                                  ip_protocol=ip_protocol,
                                  ip_ranges=ip_ranges))
    return ip_rules


def add_generic_firewall_rules(device: AWSDeviceAdapter, group_name: str, source: str,
                               direction: str, rule_list: List[AWSIPRule]):
    for rule in rule_list:
        try:
            from_port = rule.from_port
        except Exception:
            from_port = None

        try:
            to_port = rule.to_port
        except Exception:
            to_port = None

        try:
            protocol = rule.ip_protocol
        except Exception:
            protocol = None

        try:
            targets = []
            raw_targets = rule.ip_ranges
            for raw_target in raw_targets:
                if '_Description:' in raw_target:
                    cidr, desc = raw_target.split('_Description:')
                    final_string = cidr
                    if desc:
                        final_string += f' ({desc})'

                    targets.append(final_string)
                else:
                    targets.append(raw_target)
        except Exception:
            logger.exception('Problem parsing raw targets')
            targets = []

        for target in targets:
            device.add_firewall_rule(
                name=group_name,
                source=source,
                type='Allow',
                direction=direction,
                target=target,
                protocol=protocol,
                from_port=from_port,
                to_port=to_port
            )


def describe_images_from_client_by_id(ec2_client, amis):
    """
    Described images (by ids) from a specific client by id

    :param ec2_client:
    :param amis: list of image ids to get
    :return dict: image-id -> image
    """

    # the reason I use 'Filters->image-id' and not ImageIds is because if I'd use ImageIds
    # would've raise an exception if an image is not found
    # all images are returned at once so no progress is logged
    described_images = dict()
    amis = list(amis)

    # Filters are limited, usually with 200. So we batch requests of 100
    for i in range(0, len(amis), BOTO3_FILTERS_LIMIT):
        result = ec2_client.describe_images(Filters=[{'Name': 'image-id', 'Values': amis[i:i + BOTO3_FILTERS_LIMIT]}])
        for image in result['Images']:
            described_images[image['ImageId']] = image

    return described_images


def create_custom_waiter(boto_client: boto3.session.Session.client, name: str,
                         operation: str, argument: str, delay: int = 60,
                         max_attempts: int = 8) -> Waiter:
    """Here we will attempt to configure a custom waiter and return it to
    the caller.

    :param boto_client: A boto3 client object used to interact with AWS.
    :type boto_client: boto3.session.Session.client
    :param name: The name to use for this waiter.
    :type name: str
    :param operation: The name of the operation to wait for.
    :type operation: str
    :param argument: The name of the waiter argument to wait for (it will report COMPLETED, IN_PROGRESS or FAILED)
    :type argument: str
    :param delay: The amount of time, in seconds, to wait for the *argument to report its status.
    :type delay: int
    :param max_attempts: The maximum number of times to wait before failing. Each wait is equal to *delay.
    :type max_attempts: int
    :returns custom_waiter: The waiter object that can be used in all AWS operations that have a delay.
    :type custom_waiter: botocore.waiter.Waiter
    """
    waiter_config = {
        'version': 2,
        'waiters': {
            name: {
                'operation': operation,
                'delay': delay,
                'maxAttempts': max_attempts,
                'acceptors': [
                    {
                        'matcher': 'path',
                        'expected': 'COMPLETED',
                        'argument': argument,
                        'state': 'success'
                    },
                    {
                        'matcher': 'path',
                        'expected': 'IN_PROGRESS',
                        'argument': argument,
                        'state': 'retry'
                    },
                    {
                        'matcher': 'path',
                        'expected': 'FAILED',
                        'argument': argument,
                        'state': 'failure'
                    },

                ]
            }
        }
    }
    waiter_model = WaiterModel(waiter_config)
    try:
        custom_waiter = create_waiter_with_client(waiter_name=name,
                                                  waiter_model=waiter_model,
                                                  client=boto_client)
    except WaiterError as err:
        logger.warning(f'Waiter creation failed: {err}')
        raise
        # push this up the stack and surface in aws_users

    return custom_waiter
