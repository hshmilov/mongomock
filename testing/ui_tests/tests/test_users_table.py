from ui_tests.tests.ui_test_base import TestBase


class TestUsersTable(TestBase):
    JSON_ADAPTER_FILTER = 'adapters == "json_file_adapter"'

    def test_users_fetched(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        # Search for all Json Users
        self.users_page.fill_filter(self.JSON_ADAPTER_FILTER)
        self.users_page.enter_search()
        # Wait for search to return (working so long as there is a spinner)
        self.users_page.wait_for_element_absent_by_css(self.LOADING_SPINNER_CSS, interval=10)
        assert self.users_page.count_entities() == 1

    def test_user_selection(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        first_id = self.users_page.get_first_id()
        self.users_page.click_row()
        assert f'users/{first_id}' in self.driver.current_url
