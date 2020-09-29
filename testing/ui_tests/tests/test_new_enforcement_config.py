from axonius.consts.metric_consts import SystemMetric
from test_credentials.json_file_credentials import \
    client_details as json_file_creds
from ui_tests.tests.enforcement_config_base import TestEnforcementConfigBase
from ui_tests.tests.ui_consts import JSON_ADAPTER_NAME


class TestNewEnforcementConfig(TestEnforcementConfigBase):
    def test_new(self):
        self.adapters_page.clean_adapter_servers(JSON_ADAPTER_NAME)
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.select_trigger()
        self.enforcements_page.select_saved_view(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.check_scheduling()
        self.enforcements_page.check_conditions()
        self.enforcements_page.check_condition_added()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)
        assert self.axonius_system.gui.log_tester.is_metric_in_log(SystemMetric.ENFORCEMENT_RAW,
                                                                   self.ENFORCEMENT_CHANGE_NAME)
        # restore JSON client
        self.adapters_page.add_server(json_file_creds, JSON_ADAPTER_NAME)
        self.adapters_page.wait_for_server_green()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(self.ENFORCEMENT_CHANGE_NAME)
