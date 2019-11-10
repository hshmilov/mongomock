import json
import logging

from aws_adapter.connection.structures import AWSDeviceAdapter, AWSLambda, AWSLambdaPolicy
from aws_adapter.connection.utils import get_paginated_marker_api, parse_bucket_policy_statements
from axonius.utils.datetime import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


def query_devices_by_client_by_source_lambda(client_data: dict) -> dict:
    lambda_client = client_data.get('lambda')
    if lambda_client is not None:
        try:
            # If an exception appears, its probably a privilege exception, so we show it just once to not spam
            did_policy_exception_appear = False
            for function_page in get_paginated_marker_api(lambda_client.list_functions):
                for function in (function_page.get('Functions') or []):
                    function_arn = function.get('FunctionArn')
                    if not function_arn:
                        continue

                    function_raw = dict(function)

                    try:
                        function_raw['policy'] = lambda_client.get_policy(FunctionName=function_arn)['Policy']
                    except Exception as e:
                        if 'the resource you requested does not exist' in str(e).lower():
                            # This is a legitimate error, not all lambda's have functions
                            continue
                        if not did_policy_exception_appear:
                            logger.exception(f'Could not get policy for function {function_arn}')
                            did_policy_exception_appear = True

                    yield function_raw
        except Exception:
            logger.exception(f'Problem fetching data for lambda')


def parse_raw_data_inner_lambda(
        device: AWSDeviceAdapter,
        raw_data: dict,
) -> AWSDeviceAdapter:
    device.id = 'aws-lambda-' + raw_data['FunctionArn']
    device.cloud_provider = 'AWS'
    device.cloud_id = raw_data['FunctionArn']
    device.aws_device_type = 'Lambda'
    device.name = raw_data.get('FunctionName')

    subnets = (raw_data.get('VpcConfig') or {}).get('SubnetIds')
    security_groups = (raw_data.get('VpcConfig') or {}).get('SecurityGroupIds')
    layers = [layer.get('Arn') for layer in (raw_data.get('Layers') or []) if layer.get('Arn')]

    policy = None
    try:
        policy_raw = raw_data.get('policy')
        if policy_raw:
            policy_parsed = {}
            try:
                policy_parsed = json.loads(policy_raw)
            except Exception:
                pass
            policy = AWSLambdaPolicy(
                raw=policy_raw,
                statements=parse_bucket_policy_statements(policy_parsed)
            )
    except Exception:
        logger.exception(f'Failed parsing policies')

    lambda_data = AWSLambda(
        name=raw_data.get('FunctionName'),
        arn=raw_data.get('FunctionArn'),
        runtime=raw_data.get('Runtime'),
        role=raw_data.get('Role'),
        handler=raw_data.get('Handler'),
        code_size=raw_data.get('CodeSize') if isinstance(raw_data.get('CodeSize'), int) else None,
        description=raw_data.get('Description'),
        timeout=raw_data.get('Timeout') if isinstance(raw_data.get('Timeout'), int) else None,
        memory_size=raw_data.get('MemorySize') if isinstance(raw_data.get('MemorySize'), int) else None,
        last_modified=parse_date(raw_data.get('LastModified')),
        code_sha_256=raw_data.get('CodeSha256'),
        version=raw_data.get('Version'),
        subnets=subnets if isinstance(subnets, list) else None,
        security_groups=security_groups if isinstance(security_groups, list) else None,
        vpc_id=(raw_data.get('VpcConfig') or {}).get('VpcId'),
        kms_key_arn=raw_data.get('KMSKeyArn'),
        tracing_config_mode=(raw_data.get('TracingConfig') or {}).get('Mode'),
        master_arn=raw_data.get('MasterArn'),
        revision_id=raw_data.get('RevisionId'),
        layers=layers if layers else None,
        policy=policy,
    )

    device.lambda_data = lambda_data
    device.set_raw(raw_data)
    return device
