import pytest
from selenium.common.exceptions import NoSuchElementException

from ui_tests.tests.enforcement_config_base import TestEnforcementConfigBase


class TestSaveQueryDeletion(TestEnforcementConfigBase):
    def test_save_query_deletion(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.fill_enforcement_name(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        self.enforcements_page.select_saved_view(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(self.ENFORCEMENT_CHANGE_NAME)

        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.check_query_by_name(self.ENFORCEMENT_CHANGE_NAME)
        self.devices_queries_page.remove_selected_queries(confirm=True)
        self.driver.refresh()
        with pytest.raises(NoSuchElementException):
            self.devices_queries_page.find_query_row_by_name(self.ENFORCEMENT_CHANGE_NAME)

        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_enforcement(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        text = self.enforcements_page.get_saved_query_text()
        # Currently only id appear for the deleted query, rather than its name
        # formatted = f'{ENFORCEMENT_CHANGE_NAME} (deleted)'
        assert 'deleted' in text
