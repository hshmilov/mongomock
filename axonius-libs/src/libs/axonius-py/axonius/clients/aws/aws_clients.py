"""
returns aws boto3 clients (boto3.client or boto3.resource) based on params
"""
import functools

import boto3

from botocore.config import Config
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session


def get_assumed_session(
        role_arn: str,
        region_name: str,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        aws_config: Config = None
):
    """STS Role assume a boto3.Session

    With automatic credential renewal.
    Notes: We have to poke at botocore internals a few times
    """
    session_credentials = RefreshableCredentials.create_from_metadata(
        metadata=functools.partial(
            boto3_role_credentials_metadata_maker, role_arn, aws_access_key_id, aws_secret_access_key, aws_config)(),
        refresh_using=functools.partial(
            boto3_role_credentials_metadata_maker, role_arn, aws_access_key_id, aws_secret_access_key, aws_config),
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
        aws_config: Config = None
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
    sts_client = current_session.client('sts', config=aws_config)
    assumed_role_object = sts_client.assume_role(
        RoleArn=role_arn,
        DurationSeconds=60 * 15,  # The minimum possible, because we want to support any customer config
        RoleSessionName='Axonius'
    )

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
    :return:
    """

    aws_config = Config(proxies={'https': https_proxy}) if https_proxy else None

    if assumed_role_arn:
        session = get_assumed_session(
            assumed_role_arn,
            sts_region_name,
            aws_access_key_id,
            aws_secret_access_key,
            aws_config
        )
    else:
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
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
    return session.client(client_name, region_name=region_name, config=aws_config)
