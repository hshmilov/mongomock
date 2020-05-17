from compliance.utils.account_report import AccountReport


class AzureAccountReport(AccountReport):
    # pylint: disable=arguments-differ
    def add_rule(self, *args, **kwargs):
        return super().add_rule(*args, cis_json_dict=self.azure_rules_by_section, **kwargs)

    # pylint: disable=arguments-differ
    def add_rule_error(self, *args, **kwargs):
        return self.add_rule_error(*args, cis_json_dict=self.azure_rules_by_section, **kwargs)
