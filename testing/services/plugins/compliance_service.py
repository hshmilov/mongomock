import logging
import pytest

from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture
from services.updatable_service import UpdatablePluginMixin
from axonius.db_migrations import db_migration
from axonius.consts.compliance_consts import COMPLIANCE_RULES_COLLECTIONS
from axonius.compliance.compliance import get_compliance_default_rules

logger = logging.getLogger(f'axonius.{__name__}')


class ComplianceService(PluginService, UpdatablePluginMixin):
    def __init__(self):
        super().__init__('compliance')

    def _migrate_db(self):
        super()._migrate_db()
        self._run_all_migrations()

    @db_migration(raise_on_failure=False)
    def _update_schema_version_1(self):
        print('upgrade to schema 1')
        self._update_aws_rules()
        self._update_azure_rules()

    @db_migration(raise_on_failure=False)
    def _update_schema_version_2(self):
        print('Upgrade to schema 2: add oracle cloud default rules')
        self._update_oracle_cloud_rules()

    @staticmethod
    def _create_cis_rule(rule):
        return {
            'rule_name': rule.get('rule_name'),
            'category': rule.get('category'),
            'description': rule.get('description'),
            'remediation': rule.get('remediation'),
            'cis': rule.get('cis'),
            'section': rule.get('section'),
            'include_in_score': True}

    def _update_aws_rules(self):
        rules = get_compliance_default_rules('aws').get('rules')
        aws_rules_collection = self.db.get_collection(self.plugin_name, COMPLIANCE_RULES_COLLECTIONS['aws'])
        rules_to_insert = []
        for rule in rules:
            rules_to_insert.append(self._create_cis_rule(rule))
        aws_rules_collection.insert_many(rules_to_insert)

    def _update_azure_rules(self):
        rules = get_compliance_default_rules('azure').get('rules')
        azure_rules_collection = self.db.get_collection(self.plugin_name, COMPLIANCE_RULES_COLLECTIONS['azure'])
        rules_to_insert = []
        for rule in rules:
            rules_to_insert.append(self._create_cis_rule(rule))
        azure_rules_collection.insert_many(rules_to_insert)

    def _update_oracle_cloud_rules(self):
        rules = get_compliance_default_rules('oracle_cloud').get('rules')
        oracle_cloud_rules_collection = self.db.get_collection(
            self.plugin_name, COMPLIANCE_RULES_COLLECTIONS['oracle_cloud'])
        rules_to_insert = []
        for rule in rules:
            rules_to_insert.append(self._create_cis_rule(rule))
        oracle_cloud_rules_collection.insert_many(rules_to_insert)


@pytest.fixture(scope='module')
def compliance_fixture(request):
    service = ComplianceService()
    initialize_fixture(request, service)
    return service
