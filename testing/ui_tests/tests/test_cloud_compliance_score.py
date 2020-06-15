from test_credentials.test_gui_credentials import AXONIUS_USER
from test_credentials.test_aws_credentials import client_details as aws_client_details
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AWS_ADAPTER_NAME, AWS_ADAPTER
from services.adapters.aws_service import AwsService
from services.plugins.compliance_service import ComplianceService


class TestCloudComplianceScore(TestBase):

    def test_compliance_score(self):
        self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
        self.settings_page.toggle_compliance_feature()

        with AwsService().contextmanager(take_ownership=True), \
                ComplianceService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[0][0])

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.compliance_page.switch_to_page()
            self.compliance_page.wait_for_table_to_be_responsive()

            failed_rules = self.compliance_page.get_total_failed_rules()
            passed_rules = self.compliance_page.get_total_passed_rules()
            current_score = self.compliance_page.get_current_score_value()

            assert round((passed_rules / (passed_rules + failed_rules)) * 100) == current_score

            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)

        self.wait_for_adapter_down(AWS_ADAPTER)
        self.settings_page.restore_feature_flags(True)

    def test_compliance_rules_exclude(self):
        self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
        self.settings_page.toggle_compliance_feature()

        with AwsService().contextmanager(take_ownership=True), \
                ComplianceService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[0][0])

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()

            self.compliance_page.switch_to_page()
            self.compliance_page.wait_for_table_to_be_responsive()
            rules = self.compliance_page.get_all_rules()
            rules_initial_len = len(rules)

            self.compliance_page.open_rules_dialog()
            assert self.compliance_page.is_score_rules_modal_visible()
            self.compliance_page.toggle_exclude_rule([1, 5])  # exclude the first and fifth rules
            self.compliance_page.save_score_rules()
            self.compliance_page.wait_for_table_to_be_responsive()
            rules = self.compliance_page.get_all_rules()
            assert rules_initial_len == len(rules) + 2

            self.compliance_page.open_rules_dialog()
            assert self.compliance_page.is_score_rules_modal_visible()
            self.compliance_page.toggle_exclude_rule([1, 5])  # include the first and fifth rules
            self.compliance_page.save_score_rules()
            self.compliance_page.wait_for_table_to_be_responsive()
            rules = self.compliance_page.get_all_rules()
            assert rules_initial_len == len(rules)

            self.compliance_page.open_rules_dialog()
            assert self.compliance_page.is_score_rules_modal_visible()
            self.compliance_page.toggle_exclude_rule([1])  # exclude first rule, without saving.
            self.compliance_page.close_without_save_rules_dialog()
            assert not self.compliance_page.is_score_rules_modal_visible()
            rules = self.compliance_page.get_all_rules()
            assert rules_initial_len == len(rules)

            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)

        self.wait_for_adapter_down(AWS_ADAPTER)
        self.settings_page.restore_feature_flags(True)
