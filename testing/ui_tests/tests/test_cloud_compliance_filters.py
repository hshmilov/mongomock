import pytest

from test_credentials.test_gui_credentials import AXONIUS_USER
from test_credentials.test_aws_credentials import client_details as aws_client_details
from test_credentials.test_azure_credentials import client_details as azure_client_details
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AWS_ADAPTER_NAME, AWS_ADAPTER, AZURE_ADAPTER, AZURE_ADAPTER_NAME
from services.adapters.aws_service import AwsService
from services.adapters.azure_service import AzureService
from services.plugins.compliance_service import ComplianceService


class TestCloudComplianceFilters(TestBase):

    RULE_FILTER = '1.1 Avoid the use of the "root" Account'
    CATEGORY_FILTER = 'Logging'

    AZURE_CIS_TITLE = 'CIS Microsoft Azure Foundations Benchmark V1.1'
    AZURE_RULE_FILTER = '2.1 Ensure that standard pricing tier is selected'
    AZURE_CATEGORY_FILTER = 'Networking'
    AZURE_EMPTY_RULE_FILTER = '1.3 Ensure that there are no guest users'

    def test_compliance_filters(self):
        self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
        self.settings_page.toggle_compliance_feature()

        with AwsService().contextmanager(take_ownership=True), \
                ComplianceService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[0][0])

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.compliance_page.switch_to_page()

            self.compliance_page.open_rule_filter_dropdown()
            self.compliance_page.toggle_filter(self.RULE_FILTER)
            rules = self.compliance_page.get_all_rules()
            assert len(rules) == 1
            self.compliance_page.toggle_filter(self.RULE_FILTER)

            self.compliance_page.open_category_filter_dropdown()
            self.compliance_page.toggle_filter(self.CATEGORY_FILTER)
            rules = self.compliance_page.get_all_rules()
            assert len(rules) == 9

            # Testing the that filter is saved on the cis state.
            self.dashboard_page.switch_to_page()
            self.compliance_page.switch_to_page()
            rules = self.compliance_page.get_all_rules()
            assert len(rules) == 9

            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)

        self.wait_for_adapter_down(AWS_ADAPTER)
        self.settings_page.restore_feature_flags(True)

    @pytest.mark.skip('AX-7870')
    def test_compliance_aggregated_view(self):

        def parse_rule_result(result):
            [failed_str, checked_str] = result.split('/')
            return [int(failed_str), int(checked_str)]

        self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
        self.settings_page.toggle_compliance_feature()

        with AwsService().contextmanager(take_ownership=True), \
                ComplianceService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[0][0])
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[1][0])

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.compliance_page.switch_to_page()

            assert self.compliance_page.assert_default_number_of_rules()

            self.compliance_page.open_accounts_filter_dropdown()
            num_of_accounts = self.compliance_page.get_number_of_account_filter_options()
            assert num_of_accounts == 2

            accounts = self.compliance_page.get_all_accounts_options()
            self.compliance_page.toggle_filter(accounts[0])
            assert self.compliance_page.assert_default_number_of_rules()
            first_account_rules_results = [parse_rule_result(result) for result in
                                           self.compliance_page.get_all_rules_results()]

            self.compliance_page.open_accounts_filter_dropdown()
            self.compliance_page.toggle_filter(accounts[0])
            self.compliance_page.toggle_filter(accounts[1])

            assert self.compliance_page.assert_default_number_of_rules()
            second_account_rules_results = [parse_rule_result(result) for result in
                                            self.compliance_page.get_all_rules_results()]

            merged_results = []
            for index, result in enumerate(first_account_rules_results):
                merged_result = [result[0] + second_account_rules_results[index][0],
                                 result[1] + second_account_rules_results[index][1]]
                merged_results.append(merged_result)

            self.compliance_page.open_accounts_filter_dropdown()
            self.compliance_page.toggle_filter(accounts[1])  # Uncheck all accounts.

            all_rules_results = [parse_rule_result(result) for result in
                                 self.compliance_page.get_all_rules_results()]

            for index, result in enumerate(all_rules_results):
                assert result[0] == merged_results[index][0]  # Check failed rules.
                assert result[1] == merged_results[index][1]  # Check checked rules.

            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)

        self.wait_for_adapter_down(AWS_ADAPTER)
        self.settings_page.restore_feature_flags(True)

    def test_compliance_failed_rules_toggle(self):
        self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
        self.settings_page.toggle_compliance_feature()

        with AwsService().contextmanager(take_ownership=True), \
                ComplianceService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
            self.adapters_page.connect_adapter(AWS_ADAPTER_NAME, aws_client_details[0][0])

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.compliance_page.switch_to_page()

            self.compliance_page.wait_for_table_to_be_responsive()
            assert self.compliance_page.assert_default_number_of_rules()

            total_failed_rules = self.compliance_page.get_total_failed_rules()
            self.compliance_page.toggle_failed_rules()
            self.compliance_page.wait_for_table_to_be_responsive()
            total_failed_rules_only = self.compliance_page.get_total_rules_count()

            assert total_failed_rules_only == total_failed_rules

            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)

        self.wait_for_adapter_down(AWS_ADAPTER)
        self.settings_page.restore_feature_flags(True)

    def test_compliance_azure_filters(self):
        self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
        self.settings_page.toggle_compliance_feature()

        with AzureService().contextmanager(take_ownership=True), \
                ComplianceService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AZURE_ADAPTER_NAME)
            self.adapters_page.create_new_adapter_connection(AZURE_ADAPTER_NAME, azure_client_details)

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.compliance_page.switch_to_page()

            self.compliance_page.select_cis_by_title(self.AZURE_CIS_TITLE)
            self.compliance_page.assert_azure_default_number_of_rules()
            self.compliance_page.open_rule_filter_dropdown()
            self.compliance_page.toggle_filter(self.AZURE_RULE_FILTER)
            rules = self.compliance_page.get_all_rules()
            assert len(rules) == 1
            self.compliance_page.toggle_filter(self.AZURE_RULE_FILTER)

            self.compliance_page.open_category_filter_dropdown()
            self.compliance_page.toggle_filter(self.AZURE_CATEGORY_FILTER)
            rules = self.compliance_page.get_all_rules()
            assert len(rules) == 5

            # Testing the that filter is saved on the cis state.
            self.dashboard_page.switch_to_page()
            self.compliance_page.switch_to_page()
            rules = self.compliance_page.get_all_rules()
            assert len(rules) == 5

            # Testing rule and different category filter.
            self.compliance_page.open_rule_filter_dropdown()
            self.compliance_page.toggle_filter(self.AZURE_EMPTY_RULE_FILTER)
            rules = self.compliance_page.get_all_rules()
            assert len(rules) == 0

            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(AZURE_ADAPTER_NAME)

        self.wait_for_adapter_down(AZURE_ADAPTER)
        self.settings_page.restore_feature_flags(True)
