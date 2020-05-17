# pylint: disable=too-many-branches, too-many-nested-blocks
import logging

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui

logger = logging.getLogger(f'axonius.{__name__}')


class CISAzureCategory6:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()

    @cis_rule('6.1')
    def check_cis_azure_6_1(self, **kwargs):
        """
        6.1 Ensure that RDP access is restricted from the internet
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

    @cis_rule('6.2')
    def check_cis_azure_6_2(self, **kwargs):
        """
        6.2 Ensure that SSH access is restricted from the internet
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

    @cis_rule('6.3')
    def check_cis_azure_6_3(self, **kwargs):
        """
        6.3 Ensure no SQL Databases allow ingress 0.0.0.0/0 (ANY IP)
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

    @cis_rule('6.4')
    def check_cis_azure_6_4(self, **kwargs):
        """
        6.4 Ensure that Network Security Group Flow Log retention period is 'greater than 90 days'
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

    @cis_rule('6.5')
    def check_cis_azure_6_5(self, **kwargs):
        """
        6.5 Ensure that Network Watcher is 'Enabled'
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
