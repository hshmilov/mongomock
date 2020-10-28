from compliance.utils.account_report import AccountReport


class OracleCloudAccountReport(AccountReport):
    # pylint: disable=arguments-differ
    def add_rule(self, *args, **kwargs):
        return super().add_rule(*args, cis_json_dict=self.rules_by_section['oracle_cloud'], **kwargs)

    # pylint: disable=arguments-differ
    def add_rule_error(self, *args, **kwargs):
        return super().add_rule_error(*args, cis_json_dict=self.rules_by_section['oracle_cloud'], **kwargs)
