"""
Generates an AWS CIS report per one account
"""
import logging
from typing import Tuple

from axonius.clients.aws.aws_clients import get_boto3_session, get_boto3_client_by_session
from compliance.utils.account_report import AccountReport
from compliance.aws_cis.aws_cis_rules import generate_rules, generate_failed_report
from compliance.utils.cis_utils import AWS_CIS_DEFAULT_REGION

logger = logging.getLogger(f'axonius.{__name__}')


def get_session_by_account_dict(account_dict: dict):
    sts_region_name = AWS_CIS_DEFAULT_REGION if account_dict.get('get_all_regions') else account_dict.get('region_name')
    if account_dict.get('assumed_role_arn'):
        extra_args = {
            'assumed_role_arn': account_dict['assumed_role_arn'],
            'sts_region_name': sts_region_name
        }
    else:
        extra_args = {}

    if account_dict.get('use_attached_iam_role') is True:
        aws_access_key_id = None
        aws_secret_access_key = None
    else:
        aws_access_key_id = account_dict.get('aws_access_key_id')
        aws_secret_access_key = account_dict.get('aws_secret_access_key')

    return get_boto3_session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        https_proxy=account_dict.get('https_proxy'),
        **extra_args
    )


def generate_report_for_aws_account(account_dict: dict) -> Tuple[str, str, dict]:
    account_name = account_dict.get('name') or 'unknown'
    logger.info(f'Parsing account {account_name}')
    report = AccountReport()

    account_id = account_dict.get('assumed_role_arn') or account_dict.get('aws_access_key_id', 'attached-profile')
    account_name = account_id

    if account_dict.get('use_attached_iam_role') is True and not account_dict.get('assumed_role_arn'):
        account_name = 'AWS Attached Role'

    try:
        session = get_session_by_account_dict(account_dict)
    except Exception as e:
        logger.exception(f'Exception while generating report for {account_name} - could not get initial session')
        generate_failed_report(report, f'Could not generate aws connection: {str(e)}')
        return account_id.strip() if account_id else None, \
            account_name.strip() if account_name else None, \
            report.get_json()

    try:
        sts_client = get_boto3_client_by_session(
            'sts',
            session,
            AWS_CIS_DEFAULT_REGION if account_dict.get('get_all_regions') else account_dict.get('region_name',
                                                                                                AWS_CIS_DEFAULT_REGION),
            account_dict.get('https_proxy')
        )

        account_id_number = sts_client.get_caller_identity()['Account']
        account_dict['account_id_number'] = account_id_number
    except Exception:
        logger.exception(f'Could not get account id for {account_name}')
        account_id_number = None

    try:
        iam_client = get_boto3_client_by_session(
            'iam',
            session,
            AWS_CIS_DEFAULT_REGION if account_dict.get('get_all_regions') else account_dict.get('region_name'),
            account_dict.get('https_proxy')
        )

        account_alias = iam_client.list_account_aliases().get('AccountAliases') or []
        account_alias = account_alias[0] if account_alias else None
    except Exception:
        logger.exception(f'Could not get account alias for {account_name}')
        account_alias = None

    if account_id_number and account_alias:
        account_name = f'{account_alias} ({account_id_number})'
    elif account_alias:
        account_name = str(account_alias)
    elif account_id_number:
        account_name = str(account_id_number)

    try:
        generate_rules(report, session, account_dict)
    except Exception:
        logger.exception(f'Exception while generating rules for account {account_name}')
    return account_id.strip() if account_id else None, \
        account_name.strip() if account_name else None, \
        report.get_json()
