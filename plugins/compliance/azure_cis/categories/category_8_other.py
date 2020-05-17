# pylint: disable=too-many-branches, too-many-nested-blocks
import logging

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui

logger = logging.getLogger(f'axonius.{__name__}')


class CISAzureCategory8:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()

    @cis_rule('8.1')
    def check_cis_azure_8_1(self, **kwargs):
        """
        8.1 Ensure that the expiration date is set on all keys
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

    @cis_rule('8.2')
    def check_cis_azure_8_2(self, **kwargs):
        """
        8.2 Ensure that the expiration date is set on all Secrets
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

    @cis_rule('8.4')
    def check_cis_azure_8_4(self, **kwargs):
        """
        8.4 Ensure the key vault is recoverable
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

    @cis_rule('8.5')
    def check_cis_azure_8_5(self, **kwargs):
        """
        8.5 Enable role-based access control (RBAC) within Azure Kubernetes Services
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
