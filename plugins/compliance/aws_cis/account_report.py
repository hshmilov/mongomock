import json
import logging
import os
from enum import Enum

from typing import Tuple, Optional

logger = logging.getLogger(f'axonius.{__name__}')
AWS_CIS_RULES_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'aws_cis_rules.json')


class RuleStatus(Enum):
    Passed = 'Passed'
    Failed = 'Failed'


class AccountReport:
    def __init__(self):
        self.rules = []
        self.sections_added = []
        with open(AWS_CIS_RULES_FILE, 'rt') as f:
            self.rules_by_section = json.loads(f.read())

    def add_rule(
            self,
            status: RuleStatus,
            section: str,
            results: Tuple[int, int],
            affected_entities: int,
            entities_results: str,
            entities_results_query: Optional[dict] = None,
    ):
        if section in self.sections_added:
            logger.critical(f'section {section} has already been added, not continuing')
            return

        rule_text = self.rules_by_section.get(section) or {}
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
            error: Optional[str] = None):
        if section in self.sections_added:
            logger.critical(f'section {section} has already been added, not continuing')
            return

        rule_text = self.rules_by_section.get(section) or {}
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

    def get_json(self):
        return {
            'status': 'ok',
            'rules': self.rules
        }
