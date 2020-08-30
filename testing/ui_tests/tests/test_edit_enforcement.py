from flaky import flaky

from ui_tests.tests.enforcement_config_base import TestEnforcementConfigBase


class TestEditEnforcement(TestEnforcementConfigBase):
    @flaky(max_runs=3)
    def test_edit_enforcement(self):
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
        self.enforcements_page.check_conditions()
        self.enforcements_page.check_condition_subracted()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_be_responsive()
        self.enforcements_page.click_enforcement(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.click_edit_button()
        # uncheck Below
        self.enforcements_page.check_condition_subracted()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        # make sure it is now 1
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(self.ENFORCEMENT_CHANGE_NAME)
