from ui_tests.tests.ui_test_base import TestBase


class TestUsersTable(TestBase):
    JSON_ADAPTER_FILTER = 'adapters == "json_file_adapter"'

    def test_users_fetched(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        # Wait for search to return (working so long as there is a spinner)
        self.users_page.wait_for_element_absent_by_css(self.LOADING_SPINNER_CSS)
        assert self.users_page.count_entities() == self.axonius_system.get_users_db().count()

    def test_user_selection(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        first_id = self.users_page.find_first_id()
        self.users_page.click_row()
        assert f'users/{first_id}' in self.driver.current_url
