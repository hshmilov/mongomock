from ui_tests.tests.enforcement_config_base import TestEnforcementConfigBase


class TestEnforcementConfig(TestEnforcementConfigBase):
    VIEW_TASKS_CSS = '#view_tasks'

    def test_enforcement_from_saved_query(self):
        self._create_enforcement_change_query()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.find_query_row_by_name(self.ENFORCEMENT_CHANGE_NAME).click()
        self.devices_queries_page.enforce_selected_query()

        self.adapters_page.wait_for_element_absent_by_css(self.VIEW_TASKS_CSS)
        self.enforcements_page.find_existing_trigger()
        self.enforcements_page.select_trigger()
        assert self.enforcements_page.get_saved_query_text() == self.ENFORCEMENT_CHANGE_NAME
