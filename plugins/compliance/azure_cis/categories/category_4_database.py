# pylint: disable=too-many-branches, too-many-nested-blocks
import logging

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui

logger = logging.getLogger(f'axonius.{__name__}')


class CISAzureCategory4:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()

    @cis_rule('4.1')
    def check_cis_azure_4_1(self, **kwargs):
        """
        4.1 Ensure that 'Auditing' is set to 'On'
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

    @cis_rule('4.2')
    def check_cis_azure_4_2(self, **kwargs):
        """
        4.2 Ensure that 'AuditActionGroups' in 'auditing' policy for a SQL server is set properly
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

    @cis_rule('4.3')
    def check_cis_azure_4_3(self, **kwargs):
        """
        4.3 Ensure that 'Auditing' Retention is 'greater than 90 days'
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

    @cis_rule('4.4')
    def check_cis_azure_4_4(self, **kwargs):
        """
        4.4 Ensure that 'Advanced Data Security' on a SQL server is set to 'On'
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

    @cis_rule('4.5')
    def check_cis_azure_4_5(self, **kwargs):
        """
        4.5 Ensure that 'Threat Detection types' is set to 'All'
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

    @cis_rule('4.6')
    def check_cis_azure_4_6(self, **kwargs):
        """
        4.6 Ensure that 'Send alerts to' is set
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

    @cis_rule('4.7')
    def check_cis_azure_4_7(self, **kwargs):
        """
        4.7 Ensure that 'Email service and co-administrators' is 'Enabled'
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

    @cis_rule('4.8')
    def check_cis_azure_4_8(self, **kwargs):
        """
        4.8 Ensure that Azure Active Directory Admin is configured
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

    @cis_rule('4.9')
    def check_cis_azure_4_9(self, **kwargs):
        """
        4.9 Ensure that 'Data encryption' is set to 'On' on a SQL Database
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

    @cis_rule('4.10')
    def check_cis_azure_4_10(self, **kwargs):
        """
        4.10 Ensure SQL server's TDE protector is encrypted with BYOK (Use your own key)
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

    @cis_rule('4.11')
    def check_cis_azure_4_11(self, **kwargs):
        """
        4.11 Ensure 'Enforce SSL connection' is set to 'ENABLED' for MySQL Database Server
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

    @cis_rule('4.12')
    def check_cis_azure_4_12(self, **kwargs):
        """
        4.12 Ensure server parameter 'log_checkpoints' is set to 'ON' for PostgreSQL Database Server
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

    @cis_rule('4.13')
    def check_cis_azure_4_13(self, **kwargs):
        """
        4.13 Ensure 'Enforce SSL connection' is set to 'ENABLED' for PostgreSQL Database Server
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

    @cis_rule('4.14')
    def check_cis_azure_4_14(self, **kwargs):
        """
        4.14 Ensure server parameter 'log_connections' is set to 'ON' for PostgreSQL Database Server
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

    @cis_rule('4.15')
    def check_cis_azure_4_15(self, **kwargs):
        """
        4.15 Ensure server parameter 'log_disconnections' is set to 'ON' for PostgreSQL Database Server
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

    @cis_rule('4.16')
    def check_cis_azure_4_16(self, **kwargs):
        """
        4.16 Ensure server parameter 'log_duration' is set to 'ON' for PostgreSQL Database Server
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

    @cis_rule('4.17')
    def check_cis_azure_4_17(self, **kwargs):
        """
        4.17 Ensure server parameter 'connection_throttling' is set to 'ON' for PostgreSQL Database Server
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

    @cis_rule('4.18')
    def check_cis_azure_4_18(self, **kwargs):
        """
        4.18 Ensure server parameter 'log_retention_days' is greater than 3 days for PostgreSQL Database Server
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

    @cis_rule('4.19')
    def check_cis_azure_4_19(self, **kwargs):
        """
        4.19 Ensure that Azure Active Directory Admin is configured
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
