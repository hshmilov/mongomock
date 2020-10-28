"""
Generates an Azure CIS report per one account
"""
import logging
from typing import Tuple

from axonius.clients.oracle_cloud.connection import OracleCloudConnection
from axonius.clients.oracle_cloud.consts import ORACLE_TENANCY
from compliance.oracle_cloud_cis.oracle_cloud_cis_rules import generate_rules, generate_failed_report
from compliance.utils.OracleCloudAccountReport import OracleCloudAccountReport

logger = logging.getLogger(f'axonius.{__name__}')


def get_session_by_account_dict(account_dict: dict) -> OracleCloudConnection:

    with OracleCloudConnection(client_config=account_dict,
                               key_content=account_dict.get('key_content')) as connection:
        return connection


def generate_report_for_oracle_cloud_account(account_dict: dict) -> Tuple[str, str, dict]:
    account_name = account_dict.get('name') or 'unknown'
    logger.info(f'Parsing account {account_name}')
    report = OracleCloudAccountReport()

    account_id = account_dict[ORACLE_TENANCY]

    try:
        oracle_client = get_session_by_account_dict(account_dict)
    except Exception as e:
        logger.exception(f'Exception while generating Oracle Cloud report for {account_name}'
                         f' - could not get initial session')
        generate_failed_report(report, f'Could not generate oracle cloud connection: {str(e)}')
        return account_id.strip(), account_name.strip(), report.get_json()

    try:
        generate_rules(report, oracle_client, account_dict)
    except Exception:
        logger.exception(f'Exception while generating rules for Oracle account {account_name}')
    return account_id.strip(), account_name.strip(), report.get_json()
