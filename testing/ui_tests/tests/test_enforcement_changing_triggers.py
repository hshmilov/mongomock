from ui_tests.tests.enforcement_config_base import TestEnforcementConfigBase
from ui_tests.tests.ui_consts import JSON_ADAPTER_NAME
from test_credentials.json_file_credentials import client_details as json_file_creds


class TestEnforcementChangingTriggers(TestEnforcementConfigBase):
    def test_enforcement_changing_triggers(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        self.enforcements_page.select_saved_view(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_enforcement(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.click_edit_button()
        self.enforcements_page.check_conditions()
        self.enforcements_page.check_below()
        self.enforcements_page.fill_below_value(1)
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        # make sure it is still 1
        self.notification_page.verify_amount_of_notifications(1)

        self.adapters_page.clean_adapter_servers(JSON_ADAPTER_NAME)

        try:
            # Making the query return 0 results
            db = self.axonius_system.get_devices_db()
            result = db.update_one({'adapters.data.test_enforcement_change': 5},
                                   {'$set': {'adapters.$.data.test_enforcement_change': 4}})
            assert result.modified_count == 1
            self.base_page.run_discovery()
            # make sure it is now 2
            self.notification_page.verify_amount_of_notifications(2)

        finally:
            # restore JSON client
            self.adapters_page.add_server(json_file_creds, JSON_ADAPTER_NAME)
            self.adapters_page.wait_for_server_green()
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.wait_for_data_collection_toaster_absent()
