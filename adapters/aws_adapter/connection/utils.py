import logging
from typing import List

from aws_adapter.connection.structures import AWSS3PolicyStatement

logger = logging.getLogger(f'axonius.{__name__}')
PAGE_NUMBER_FLOOD_PROTECTION = 9000


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
