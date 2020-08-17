"""
returns aws boto3 clients (boto3.client or boto3.resource) based on params
"""
import functools
import json
import logging
import re
import time
from typing import Dict, List, Tuple, Optional

import boto3

from botocore.config import Config
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session

# pylint: disable=import-error
import pyotp

logger = logging.getLogger(f'axonius.{__name__}')

AWS_MFA_SERIAL_NUMBER = 'serial_number'
AWS_MFA_TOTP_CODE = 'totp_code'
MAX_GET_SESSION_TOKEN_RETRIES = 3
TIME_TO_SLEEP_BETWEEN_RETRIES_IN_SECONDS = 63   # 1 minute for totp code to re-generate, 3 seconds for safety
PAGE_NUMBER_FLOOD_PROTECTION = 9000


def get_session_token_with_totp(
        sts_client, aws_mfa_details: dict, aws_config: Config, identity: str, region_name: str
) -> dict:
    # Since we have multiple roles that are trying to re-create the same boto3 session using AWS MFA, and since AWS
    # allows using the TOTP only once in a minute, we have to sync the session between the different processes,
    # otherwise, each role assumption would take 1 min at least.
    # first, try using the latest dictionary we have
    from axonius.plugin_base import PluginBase
    multiprocessing_shared_dict = PluginBase.Instance.multiprocessing_shared_dict
    identity_string = f'aws_mfa_dict_{identity}'
    aws_mfa_latest_dict = multiprocessing_shared_dict.get(identity_string)
    if aws_mfa_latest_dict:
        try:
            current_session = boto3.Session(
                aws_access_key_id=aws_mfa_latest_dict['Credentials']['AccessKeyId'],
                aws_secret_access_key=aws_mfa_latest_dict['Credentials']['SecretAccessKey'],
                aws_session_token=aws_mfa_latest_dict['Credentials']['SessionToken']
            )
            current_session.client('sts', config=aws_config, region_name=region_name).get_caller_identity()
            return aws_mfa_latest_dict
        except Exception:
            logger.debug(f'Could not use latest aws mfa dict, will try to generate on our own')

    for i in range(MAX_GET_SESSION_TOKEN_RETRIES):
        try:
            new_aws_mfa_creds = sts_client.get_session_token(
                SerialNumber=aws_mfa_details.get(AWS_MFA_SERIAL_NUMBER),
                TokenCode=pyotp.TOTP(aws_mfa_details.get(AWS_MFA_TOTP_CODE)).now()
            )
            logger.debug(f'Succeeded TOTP on try {i}')
            multiprocessing_shared_dict[identity_string] = new_aws_mfa_creds
            break
        except Exception:
            logger.debug(f'Failed TOTP {i}', exc_info=True)
            time.sleep(TIME_TO_SLEEP_BETWEEN_RETRIES_IN_SECONDS)
    else:
        raise ValueError(f'Could not authenticate with TOTP')

    return new_aws_mfa_creds


def parse_aws_advanced_config(file_contents: str) -> dict:
    if not file_contents.strip():
        return {}
    try:
        config = json.loads(file_contents.strip())
    except Exception:
        raise ValueError('Error parsing advanced config file - expecting a valid json format')

    if not isinstance(config, dict):
        raise ValueError('Error parsing advanced config file - expecting a dictionary ({})')

    return config


def parse_roles_to_assume_file(file_contents: str) -> Tuple[Dict[str, Dict], List]:
    # Input validation
    failed_arns = []
    final_dict = dict()
    pattern = re.compile('^arn:aws:iam::[0-9]+:role\/.*')  # pylint: disable=anomalous-backslash-in-string
    pattern2 = re.compile('^arn:aws-us-gov:iam::[0-9]+:role\/.*')  # pylint: disable=anomalous-backslash-in-string

    if file_contents.strip().startswith('['):
        try:
            loaded_list = json.loads(file_contents)
        except Exception as e:
            raise ValueError(f'Error parsing roles file - malformed json: {str(e)}')
        if not isinstance(loaded_list, list):
            raise ValueError(f'Error parsing roles file - Did not find a list. '
                             f'The file should contain a list of dictionaries')

        for member in loaded_list:
            if not isinstance(member, dict):
                raise ValueError(f'Error parsing roles file - expecting a list of dictionaries')
            arn = member.get('arn')
            if not arn:
                raise ValueError(f'Error parsing roles file - found dictionary without "arn" value')

            if arn in final_dict:
                raise ValueError(f'Error parsing roles file - arn {arn} exists multiple times')

            final_dict[arn] = member
    elif file_contents.strip().startswith('{'):
        raise ValueError(f'Error - Did not find a list. The file should contain a list of dictionaries')
    else:
        for role_arn in file_contents.strip().split(','):
            role_arn = role_arn.strip()
            final_dict[role_arn] = {
                'arn': role_arn
            }

    for role_arn in final_dict:
        # A role must look like 'arn:aws:iam::[account_id]:role/[name_of_role]
        # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html#genref-arns
        if not pattern.match(role_arn) and not pattern2.match(role_arn):
            failed_arns.append(role_arn)

    return final_dict, failed_arns


def get_assumed_session(
        role_arn: str,
        region_name: str,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        aws_config: Config = None,
        external_id: str = None,
        aws_mfa_details: Optional[dict] = None
):
    """STS Role assume a boto3.Session

    With automatic credential renewal.
    Notes: We have to poke at botocore internals a few times
    """
    session_credentials = RefreshableCredentials.create_from_metadata(
        metadata=functools.partial(
            boto3_role_credentials_metadata_maker, role_arn, aws_access_key_id, aws_secret_access_key,
            aws_config, region_name, external_id, aws_mfa_details)(),
        refresh_using=functools.partial(
            boto3_role_credentials_metadata_maker, role_arn, aws_access_key_id, aws_secret_access_key,
            aws_config, region_name, external_id, aws_mfa_details),
        method='sts-assume-role'
    )
    role_session = get_session()
    role_session._credentials = session_credentials     # pylint: disable=protected-access
    role_session.set_config_variable('region', region_name)
    return boto3.Session(botocore_session=role_session)


def boto3_role_credentials_metadata_maker(
        role_arn: str,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        aws_config: Config = None,
        region_name: str = None,
        external_id: str = None,
        aws_mfa_details: Optional[dict] = None
):
    """
    Generates a "metadata" dict creator that is used to initialize auto-refreshing sessions.
    This is done to support auto-refreshing role-sessions; When we assume a role, we have to put a duration
    for it. when it expires, the internal botocore class will auto refresh it. This is the refresh function.
    for more information look at: https://dev.to/li_chastina/auto-refresh-aws-tokens-using-iam-role-and-boto3-2cjf
    :return:
    """
    current_session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

    sts_client = current_session.client('sts', config=aws_config, region_name=region_name)

    if aws_mfa_details:
        new_aws_mfa_creds = get_session_token_with_totp(
            sts_client, aws_mfa_details, aws_config, aws_access_key_id, region_name
        )

        current_session = boto3.Session(
            aws_access_key_id=new_aws_mfa_creds['Credentials']['AccessKeyId'],
            aws_secret_access_key=new_aws_mfa_creds['Credentials']['SecretAccessKey'],
            aws_session_token=new_aws_mfa_creds['Credentials']['SessionToken']
        )

        sts_client = current_session.client('sts', config=aws_config, region_name=region_name)

    params = {
        'RoleArn': role_arn,
        'DurationSeconds': 60 * 15,  # The minimum possible, because we want to support any customer config
        'RoleSessionName': 'Axonius',
    }

    if external_id:
        params['ExternalId'] = external_id

    assumed_role_object = sts_client.assume_role(**params)
    response = assumed_role_object['Credentials']

    credentials = {
        'access_key': response.get('AccessKeyId'),
        'secret_key': response.get('SecretAccessKey'),
        'token': response.get('SessionToken'),
        'expiry_time': response.get('Expiration').isoformat(),
    }
    return credentials


def get_boto3_session(
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        https_proxy: str = None,
        sts_region_name: str = None,
        assumed_role_arn: str = None,
        external_id: str = None,
        aws_mfa_details: Optional[dict] = None
) -> boto3.Session:
    """
    Gets a boto3.Session object with the required parameters.
    Does not verify parameters!

    :param aws_access_key_id: an optional access key. If not exists, uses an attached iam role (instance profile)
    :param aws_secret_access_key: an optional secret. If not exists, uses an attached iam role (instance profile)
    :param https_proxy: an optional https proxy
    :param sts_region_name: the region name to assume from. This could be us-east-1 if this is a regular account, or
                            a gov region if this is a gov account. This is only used to assume the role.
    :param assumed_role_arn: an optional assume role arn. If supplied, the session will be an assumed role session
    :param external_id: an optional external id string
    :param aws_mfa_details: optional MFA details
    :return:
    """

    if sts_region_name:
        sts_region_name = sts_region_name.lower()

    aws_config = Config(proxies={'https': https_proxy}) if https_proxy else None

    if assumed_role_arn:
        session = get_assumed_session(
            assumed_role_arn,
            sts_region_name,
            aws_access_key_id,
            aws_secret_access_key,
            aws_config,
            external_id,
            aws_mfa_details
        )
    else:
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=sts_region_name
        )

        if aws_mfa_details:
            sts_client = session.client('sts', config=aws_config, region_name=sts_region_name)

            new_aws_mfa_creds = get_session_token_with_totp(
                sts_client, aws_mfa_details, aws_config, aws_access_key_id, sts_region_name
            )

            session = boto3.Session(
                aws_access_key_id=new_aws_mfa_creds['Credentials']['AccessKeyId'],
                aws_secret_access_key=new_aws_mfa_creds['Credentials']['SecretAccessKey'],
                aws_session_token=new_aws_mfa_creds['Credentials']['SessionToken'],
                region_name=sts_region_name
            )

    return session


def get_boto3_client_by_session(
        client_name: str,
        session: boto3.Session,
        region_name: str,
        https_proxy: str
):
    aws_config = Config(proxies={'https': https_proxy}) if https_proxy else None
    return session.client(client_name, region_name=region_name.lower(), config=aws_config)


def get_paginated_continuation_token_api(func):
    """
    This should be in utils.py, but it needs to be accessed also by the
    enforcement center (which cannot reach the aws_adapter code), so it
    is here in aws_clients.py. This is similar to the other pagination
    methods except it uses a NextContinuationToken instead of the standard
    ContinuationToken. For functions that have not parameters, wrap this
    in a functools call. If there are parameters, wrap it in functools.partial.
    """
    continuation_token_name = None
    next_continuation_token = None
    page_number = 0

    while page_number < PAGE_NUMBER_FLOOD_PROTECTION:
        page_number += 1
        if next_continuation_token:
            result = func(**{continuation_token_name: next_continuation_token})
        else:
            result = func()

        yield result

        if result.get('NextContinuationToken'):
            continuation_token_name = 'NextContinuationToken'
        elif result.get('nextContinuationToken'):
            continuation_token_name = 'nextContinuationToken'

        if continuation_token_name:
            next_continuation_token = result.get(continuation_token_name)
        if not next_continuation_token:
            break

    if page_number == PAGE_NUMBER_FLOOD_PROTECTION:
        logger.critical('AWS Pagination (Continuation Token): Reached '
                        'page flood protection count')
