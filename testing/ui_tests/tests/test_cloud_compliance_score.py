from test_credentials.test_gui_credentials import AXONIUS_USER
from test_credentials.test_aws_credentials import client_details as aws_client_details
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AWS_ADAPTER_NAME, AWS_ADAPTER
from services.adapters.aws_service import AwsService


class TestCloudComplianceScore(TestBase):
    def test_compliance_score(self):
        self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
        self.settings_page.toggle_compliance_feature()

        with AwsService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[0][0])

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.compliance_page.switch_to_page()
            self.compliance_page.wait_for_table_to_be_responsive()

            rules_total_count = self.compliance_page.get_total_rules_count()
            passed_rules = self.compliance_page.get_total_passed_rules()
            current_score = self.compliance_page.get_current_score_value()

            assert round((passed_rules / rules_total_count) * 100) == current_score

            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)

        self.wait_for_adapter_down(AWS_ADAPTER)
        self.settings_page.restore_feature_flags(True)
