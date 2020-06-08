import logging
from enum import Enum

from typing import Tuple, Optional

from axonius.plugin_base import PluginBase
from axonius.compliance.compliance import get_compliance_rules_collection

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=protected-access


class RuleStatus(Enum):
    Passed = 'Passed'
    Failed = 'Failed'


class AccountReport:
    def __init__(self):
        self.rules = []
        self.sections_added = []
        self.plugin_base: PluginBase = PluginBase.Instance

        aws_rules_collection = get_compliance_rules_collection('aws')
        azure_rules_collection = get_compliance_rules_collection('azure')

        self.aws_rules_by_section = self._prepare_rules(aws_rules_collection.find({}))
        self.azure_rules_by_section = self._prepare_rules(azure_rules_collection.find({}))

    @staticmethod
    def _prepare_rules(rules):
        result = {}
        for rule in rules:
            result[rule['section']] = {
                'rule_name': rule['rule_name'],
                'category': rule['category'],
                'description': rule['description'],
                'remediation': rule['remediation'],
                'cis': rule['cis']}
        return result

    def add_rule(
            self,
            status: RuleStatus,
            section: str,
            results: Tuple[int, int],
            affected_entities: int,
            entities_results: str,
            entities_results_query: Optional[dict] = None,
            cis_json_dict: Optional[dict] = None    # has to be last
    ):
        if cis_json_dict is None:
            cis_json_dict = self.aws_rules_by_section
        if section in self.sections_added:
            logger.critical(f'section {section} has already been added, not continuing')
            return

        rule_text = cis_json_dict.get(section) or {}
        new_rule = {
            'status': status.value,
            'section': section,
            'rule_name': rule_text.get('rule_name'),
            'category': rule_text.get('category'),
            'description': rule_text.get('description'),
            'remediation': rule_text.get('remediation'),
            'cis': rule_text.get('cis'),
            'results': {'failed': results[0], 'checked': results[1]},
            'affected_entities': affected_entities,
            'entities_results': entities_results
        }

        if entities_results_query:
            new_rule['entities_results_query'] = entities_results_query

        self.sections_added.append(section)
        self.rules.append(new_rule)

    def add_rule_error(
            self,
            section: str,
            error: Optional[str] = None,
            cis_json_dict: Optional[dict] = None    # has to be last
    ):
        if cis_json_dict is None:
            cis_json_dict = self.aws_rules_by_section

        if section in self.sections_added:
            logger.critical(f'section {section} has already been added, not continuing')
            return

        rule_text = cis_json_dict.get(section) or {}
        new_rule = {
            'status': 'No Data',
            'section': section,
            'rule_name': rule_text.get('rule_name'),
            'category': rule_text.get('category'),
            'description': rule_text.get('description'),
            'remediation': rule_text.get('remediation'),
            'cis': rule_text.get('cis'),
            'error': error,
            'affected_entities': 0
        }

        self.sections_added.append(section)
        self.rules.append(new_rule)

        try:
            logger.debug(f'add_rule_error for {section}: {error}')
        except Exception:
            pass

    def get_json(self):
        return {
            'status': 'ok',
            'rules': self.rules
        }
