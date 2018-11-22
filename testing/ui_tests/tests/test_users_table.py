from test_credentials.json_file_credentials import USER_NAME_UNICODE
from ui_tests.tests.ui_test_base import TestBase


class TestUsersTable(TestBase):
    USER_NAME_COLUMN = 'User Name'
    DOMAIN_COLUMN = 'Domain'
    MAIL_COLUMN = 'Mail'
    QUERY_FILTER_USERNAME = 'specific_data.data.username%20%3D%3D%20regex(%22m%22)'
    QUERY_FIELDS = 'adapters,specific_data.data.image,specific_data.data.username,specific_data.' \
                   'data.domain,specific_data.data.last_seen,specific_data.data.is_admin'

    def test_users_fetched(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        # Wait for search to return (working so long as there is a spinner)
        self.users_page.wait_for_spinner_to_end()
        assert self.users_page.count_entities() == self.axonius_system.get_users_db().count()

    def test_user_selection(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        first_id = self.users_page.find_first_id()
        self.users_page.click_row()
        assert f'users/{first_id}' in self.driver.current_url

    def _test_user_sort_result(self, col_name, desc=True):
        self.users_page.click_sort_column(col_name)
        self.users_page.wait_for_spinner_to_end()
        usernames = self.users_page.get_column_data(col_name)
        assert len(usernames) > 0
        sorted_usernames = usernames.copy()
        sorted_usernames.sort(reverse=desc)
        assert usernames == sorted_usernames

    def _test_user_sort(self, col_name):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        # Test sort in one direction
        self._test_user_sort_result(col_name)
        # Test sort in the other direction
        self._test_user_sort_result(col_name, desc=False)

    def test_user_sort_by_name(self):
        self._test_user_sort(self.USER_NAME_COLUMN)

    def test_user_sort_by_domain(self):
        self._test_user_sort(self.DOMAIN_COLUMN)

    def test_unicode_char(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        self.users_page.wait_for_spinner_to_end()
        assert self.users_page.is_text_in_coloumn(self.USER_NAME_COLUMN, USER_NAME_UNICODE)

    def test_user_edit_columns(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        self.users_page.select_columns([self.MAIL_COLUMN, self.DOMAIN_COLUMN])
        assert len(self.users_page.get_column_data(self.MAIL_COLUMN))
        assert not len(self.users_page.get_column_data(self.DOMAIN_COLUMN))

    def test_user_save_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()

        self.users_page.customize_view_and_save('test_save_query', 50, self.USER_NAME_COLUMN,
                                                [self.MAIL_COLUMN, self.DOMAIN_COLUMN],
                                                self.users_page.JSON_ADAPTER_FILTER)
        view_data = self.users_page.get_all_data()

        # Load some default view, to see that the saved one changes it
        self.users_page.execute_saved_query('Users Created in Last 30 Days')
        assert self.users_page.get_all_data() != view_data

        self.users_page.clear_filter()
        self.users_page.execute_saved_query('test_save_query')

        # Check loaded data is equal to original one whose view was saved
        assert self.users_page.get_all_data() == view_data

    def test_user_export_csv(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        # filter the ui to fit the QUERY_FILTER_USERNAME of the csv
        self.users_page.query_user_name_contains('m')

        result = self.users_page.generate_csv('users',
                                              self.QUERY_FIELDS,
                                              self.QUERY_FILTER_USERNAME)
        self.users_page.assert_csv_match_ui_data(result)
