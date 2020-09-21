import logging

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass


logger = logging.getLogger(f'axonius.{__name__}')


class AzureCISRule(SmartJsonClass):
    rule_section = Field(str, 'Rule Section')


class AzureAdapterEntity(SmartJsonClass):
    # Azure CIS
    azure_cis_incompliant = ListField(AzureCISRule, 'Noncompliant CIS Azure Foundations')
    azure_account_id = Field(str, 'Account ID')

    def add_azure_cis_incompliant_rule(self, rule_section):
        try:
            self.azure_cis_incompliant.append(AzureCISRule(rule_section=rule_section))
        except Exception as e:
            logger.debug(f'Could not add Azure CIS rule: {str(e)}')
