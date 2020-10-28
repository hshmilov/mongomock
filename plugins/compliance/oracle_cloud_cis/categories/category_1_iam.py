import datetime
import logging

from axonius.clients.oracle_cloud.connection import OracleCloudConnection
from axonius.clients.oracle_cloud.consts import ORACLE_TENANCY, CIS_API_KEY_ROTATION_DAYS
from axonius.entities import EntityType
from axonius.utils.datetime import parse_date
from compliance.utils.OracleCloudAccountReport import OracleCloudAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui, get_count_incompliant_generic_cis_rule, \
    build_entities_query

logger = logging.getLogger(f'axonius.{__name__}')


class CISOracleCloudCategory1:
    def __init__(self, report: OracleCloudAccountReport, oracle: OracleCloudConnection, account_dict: dict):
        self.report = report
        self.oracle = oracle
        self._account_dict = account_dict.copy()
        self._account_id = self._account_dict.get(ORACLE_TENANCY) or 'unknown-tenancy'
        self.all_users = list(self.oracle.get_users_list())

    def get_count_incompliant(self, rule_section):
        try:
            return get_count_incompliant_generic_cis_rule(
                EntityType.Users,
                rule_section,
                self._account_id,
                'oracle_cloud'
            )
        except Exception as e:
            logger.debug(f'Error counting affected oracle cloud users for rule {rule_section}: {str(e)}')
            return 0

    def get_entities_query(self, rule_section):
        try:
            return build_entities_query(
                'users',
                rule_section,
                account_id=self._account_id,
                plugin_name='oracle_cloud_adapter',
                field_prefix='oracle_cloud'
            )
        except Exception as e:
            logger.debug(f'Error building query for affected oracle cloud users for rule {rule_section}: {str(e)}')
            return None

    @cis_rule('1.11')
    def check_cis_oracle_cloud_1_11(self, **kwargs):
        """
        1.11 ensure MFA enabled for all users with console password
        """
        rule_section = kwargs['rule_section']
        total_resources = len(self.all_users)
        errors = []
        for user in self.all_users:
            if user.is_mfa_activated:
                continue
            display_name = user.name
            errors.append(f'User {display_name} does not have MFA activated.')

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                self.get_count_incompliant(rule_section),
                errors_to_gui(errors),
                self.get_entities_query(rule_section)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )

    @cis_rule('1.12')
    def check_cis_oracle_cloud_1_12(self, **kwargs):
        """
        1.12 Ensure user API keys rotate within 90 days or less
        """
        rule_section = kwargs['rule_section']
        total_resources = len(self.all_users)
        errors = []
        for user in self.all_users:
            if not hasattr(user, 'x_api_keys'):
                continue
            for api_key in user.x_api_keys:
                days_ago_90 = parse_date(datetime.datetime.now() - datetime.timedelta(days=CIS_API_KEY_ROTATION_DAYS))
                if isinstance(api_key.time_created, datetime.datetime) and \
                        parse_date(api_key.time_created) < days_ago_90:
                    display_name = user.name
                    errors.append(f'User {display_name} has api key {api_key.fingerprint} '
                                  f'created at {api_key.time_created}')

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                self.get_count_incompliant(rule_section),
                errors_to_gui(errors),
                self.get_entities_query(rule_section)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )

    @cis_rule('1.13')
    def check_cis_oracle_cloud_1_13(self, **kwargs):
        """
        1.13 ensure api keys are not created for tenancy administrator users
        """
        rule_section = kwargs['rule_section']
        total_resources = len(self.all_users)
        errors = []
        for user in self.all_users:
            if not hasattr(user, 'x_groups'):
                continue
            if any(['admin' in x.name.lower() for x in user.x_groups]):
                if hasattr(user, 'x_api_keys') and user.x_api_keys:
                    display_name = user.name
                    errors.append(f'Admin user {display_name} has API keys.')

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                self.get_count_incompliant(rule_section),
                errors_to_gui(errors),
                self.get_entities_query(rule_section)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )
