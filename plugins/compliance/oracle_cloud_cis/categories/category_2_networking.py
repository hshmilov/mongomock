import logging

from axonius.clients.oracle_cloud.connection import OracleCloudConnection
from axonius.clients.oracle_cloud.consts import ORACLE_TENANCY
from axonius.entities import EntityType
from compliance.utils.OracleCloudAccountReport import OracleCloudAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui, \
    get_count_incompliant_generic_cis_rule, build_entities_query

logger = logging.getLogger(f'axonius.{__name__}')

QUERY_SECLISTS = 'query SecurityList resources where ' \
                 '(IngressSecurityRules.source = \'0.0.0.0/0\' && ' \
                 'IngressSecurityRules.protocol = 6 && ' \
                 'IngressSecurityRules.tcpOptions.destinationPortRange.max = {PORT} && ' \
                 'IngressSecurityRules.tcpOptions.destinationPortRange.min = {PORT})'


class CISOracleCloudCategory2:
    def __init__(self, report: OracleCloudAccountReport, oracle: OracleCloudConnection, account_dict: dict):
        self.report = report
        self.oracle = oracle
        self._account_dict = account_dict.copy()
        self._account_id = self._account_dict.get(ORACLE_TENANCY) or 'unknown-tenancy'
        self._total_resources = len(self.oracle.get_query_data(
            'query SecurityList resources'
        ).data.items)

    def get_count_incompliant(self, rule_section):
        try:
            return get_count_incompliant_generic_cis_rule(
                EntityType.Devices,
                rule_section,
                self._account_id,
                'oracle_cloud'
            )
        except Exception as e:
            logger.debug(f'Error counting affected oracle cloud devices for rule {rule_section}: {str(e)}')
            return 0

    def get_entities_query(self, rule_section):
        try:
            return build_entities_query(
                'devices',
                rule_section,
                account_id=self._account_id,
                plugin_name='oracle_cloud_adapter',
                field_prefix='oracle_cloud'
            )
        except Exception as e:
            logger.debug(f'Error building query for affected oracle cloud devices for rule {rule_section}: {str(e)}')
            return None

    @cis_rule('2.1')
    def check_cis_oracle_cloud_2_1(self, **kwargs):
        """
        2.1 Ensure no security lists allow ingress from 0.0.0.0/0 to port 22
        """
        rule_section = kwargs['rule_section']
        errors = []
        total_resources = self._total_resources
        results = self.oracle.get_query_data(QUERY_SECLISTS.format(PORT=22))
        if results.data.items:
            for result in results.data.items:
                errors.append(f'In compartment {result.compartment_id}: '
                              f'{result.resource_type} {result.display_name or result.identifier} allows '
                              f'ingress on port 22')

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                self.get_count_incompliant(rule_section),
                errors_to_gui(errors),
                self.get_entities_query(rule_section),
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )

    @cis_rule('2.2')
    def check_cis_oracle_cloud_2_2(self, **kwargs):
        """
        2.2 Ensure no security lists allow ingress from 0.0.0.0/0 to port 3389
        """
        rule_section = kwargs['rule_section']
        errors = []
        total_resources = self._total_resources
        results = self.oracle.get_query_data(QUERY_SECLISTS.format(PORT=3389))
        if results.data.items:
            for result in results.data.items:
                errors.append(f'In compartment {result.compartment_id}: '
                              f'{result.resource_type} {result.display_name or result.identifier} allows '
                              f'ingress on port 3389')

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                self.get_count_incompliant(rule_section),
                errors_to_gui(errors),
                self.get_entities_query(rule_section),
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )

    @cis_rule('2.5')
    def check_cis_oracle_cloud_2_5(self, **kwargs):
        """
        2.5 Ensure no VCNs have default security lists allow ingress from 0.0.0.0/0 to port 22
        """
        rule_section = kwargs['rule_section']
        errors = []
        vcns = self.oracle.get_vcn_infos()
        total_resources = len(vcns)
        for vcn_id in vcns:
            default_sec_list = vcns[vcn_id]['default_sec_list']
            query_base = QUERY_SECLISTS.format(PORT=22)
            full_query = f'{query_base} && identifier = \'{default_sec_list.id}\''
            results = self.oracle.get_query_data(full_query)
            if not (hasattr(results, 'data') and hasattr(results.data, 'items')):
                continue
            if results.data.items:
                errors.append(f'VCN {vcn_id}: Default security list {results.data.items[0].identifier} '
                              f'allows ingress from 0.0.0.0/0 to port 22')

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                self.get_count_incompliant(rule_section),
                errors_to_gui(errors),
                self.get_entities_query(rule_section),
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )
