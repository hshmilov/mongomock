"""
Here the actual logic happens
"""
import logging

from axonius.clients.oracle_cloud.connection import OracleCloudConnection
from axonius.compliance.oracle_cloud_cis_consts import ORACLE_CLOUD_CIS_ALL_RULES
from compliance.oracle_cloud_cis.categories.category_1_iam import CISOracleCloudCategory1
from compliance.oracle_cloud_cis.categories.category_2_networking import CISOracleCloudCategory2
from compliance.oracle_cloud_cis.categories.category_3_logging import CISOracleCloudCategory3

from compliance.utils import OracleCloudAccountReport
from compliance.utils.account_report import AccountReport

logger = logging.getLogger(f'axonius.{__name__}')


def generate_failed_report(report: AccountReport, error: str):
    for rule_section in ORACLE_CLOUD_CIS_ALL_RULES:
        report.add_rule_error(rule_section, error)


# pylint: disable=too-many-statements
def generate_rules(report: OracleCloudAccountReport, oracle: OracleCloudConnection, account_dict: dict):
    with oracle:
        category_1 = CISOracleCloudCategory1(report, oracle, account_dict)
        category_1.check_cis_oracle_cloud_1_11()
        category_1.check_cis_oracle_cloud_1_12()
        category_1.check_cis_oracle_cloud_1_13()

        category_2 = CISOracleCloudCategory2(report, oracle, account_dict)
        category_2.check_cis_oracle_cloud_2_1()
        category_2.check_cis_oracle_cloud_2_2()
        category_2.check_cis_oracle_cloud_2_5()

        category_3 = CISOracleCloudCategory3(report, oracle, account_dict)
        category_3.check_cis_oracle_cloud_3_1()
