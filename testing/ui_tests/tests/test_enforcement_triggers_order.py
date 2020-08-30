from ui_tests.tests.enforcement_config_base import TestEnforcementConfigBase


class TestEnforcementTriggersOrder(TestEnforcementConfigBase):
    def test_enforcement_triggers_order(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.add_tag_entities()
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        labels = self.enforcements_page.get_all_periods_sorted()
        assert labels == self.RECURRENCE_OPTIONS
