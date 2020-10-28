import logging

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass

logger = logging.getLogger(f'axonius.{__name__}')


class OracleCloudCISRule(SmartJsonClass):
    rule_section = Field(str, 'Rule Section')


class OracleCloudAdapterEntity(SmartJsonClass):
    # Oracle CIS
    oracle_cloud_cis_incompliant = ListField(OracleCloudCISRule, 'Noncompliant CIS Oracle Cloud Foundations')
    oracle_cloud_account_id = Field(str, 'Account ID')

    def add_oracle_cloud_cis_incompliant_rule(self, rule_section):
        try:
            self.oracle_cloud_cis_incompliant.append(OracleCloudCISRule(rule_section=rule_section))
        except Exception as e:
            logger.debug(f'Could not add Oracle Cloud CIS rule: {str(e)}')
