import logging

from axonius.clients.oracle_cloud.connection import OracleCloudConnection
from axonius.clients.oracle_cloud.consts import ORACLE_TENANCY
from compliance.utils.OracleCloudAccountReport import OracleCloudAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui

logger = logging.getLogger(f'axonius.{__name__}')


class CISOracleCloudCategory3:
    def __init__(self, report: OracleCloudAccountReport, oracle: OracleCloudConnection, account_dict: dict):
        self.report = report
        self.oracle = oracle
        self._account_dict = account_dict.copy()
        self._account_id = self._account_dict.get(ORACLE_TENANCY) or 'unknown-tenancy'

    @cis_rule('3.1')
    def check_cis_oracle_cloud_3_1(self, **kwargs):
        """
        3.1 Ensure audit log retention period is set to 365 days
        """
        rule_section = kwargs['rule_section']
        errors = []

        audit_log_days = self.oracle.cis_get_log_retention_days()
        if audit_log_days != 365:
            errors.append(f'Tenancy {self._account_id}: Retention policy is set to {audit_log_days}')
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (1, 1),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, 1),
                0,
                ''
            )
