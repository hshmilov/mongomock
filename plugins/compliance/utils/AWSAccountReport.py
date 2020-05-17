from compliance.utils.account_report import AccountReport


# This has not been refactored yet, because i don't wanna make the PR too noisy.
# But basically for order reasons we gotta replace AccountReport in AWSAccountReport anywhere in aws_cis
class AWSAccountReport(AccountReport):
    # pylint: disable=arguments-differ
    def add_rule(self, *args, **kwargs):
        return super().add_rule(*args, cis_json_dict=self.aws_rules_by_section, **kwargs)

    # pylint: disable=arguments-differ
    def add_rule_error(self, *args, **kwargs):
        return super().add_rule_error(*args, cis_json_dict=self.aws_rules_by_section, **kwargs)
