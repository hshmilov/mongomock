"""
Here the actual logic happens
"""
import logging

from axonius.clients.azure.client import AzureCloudConnection
from axonius.compliance.azure_cis_consts import AZURE_CIS_ALL_RULES
from compliance.utils import AzureAccountReport
from compliance.utils.account_report import AccountReport

logger = logging.getLogger(f'axonius.{__name__}')


def generate_failed_report(report: AccountReport, error: str):
    for rule_section in AZURE_CIS_ALL_RULES:
        report.add_rule_error(rule_section, error)


# pylint: disable=too-many-statements
def generate_rules(report: AzureAccountReport, session: AzureCloudConnection, account_dict: dict):
    pass
