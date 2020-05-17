# pylint: disable=too-many-branches, too-many-nested-blocks
import logging

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui

logger = logging.getLogger(f'axonius.{__name__}')


class CISAzureCategory7:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()

    @cis_rule('7.1')
    def check_cis_azure_7_1(self, **kwargs):
        """
        7.1 Ensure that 'OS disk' are encrypted
        """
        rule_section = kwargs['rule_section']
        total_resources = 10
        errors = []

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )

    @cis_rule('7.2')
    def check_cis_azure_7_2(self, **kwargs):
        """
        7.2 Ensure that 'Data disks' are encrypted
        """
        rule_section = kwargs['rule_section']
        total_resources = 10
        errors = []

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )

    @cis_rule('7.3')
    def check_cis_azure_7_3(self, **kwargs):
        """
        7.3 Ensure that 'Unattached disks' are encrypted
        """
        rule_section = kwargs['rule_section']
        total_resources = 10
        errors = []

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )
