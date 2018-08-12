from ui_tests.tests.ui_test_base import TestBase


class TestLifecycleSettings(TestBase):
    def test_change_schedule_rate(self):
        self.settings_page.switch_to_page()
        assert self.settings_page.get_schedule_rate_value() == self.settings_page.DEFAULT_SCHEDULE_RATE
        self.settings_page.fill_schedule_rate(-5)
        self.settings_page.find_schedule_rate_error()
        self.settings_page.click_save_button()
        self.settings_page.refresh()
        assert self.settings_page.get_schedule_rate_value() == self.settings_page.DEFAULT_SCHEDULE_RATE
