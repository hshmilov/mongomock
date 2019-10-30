from datetime import datetime
import pytz
import pytest

from ui_tests.tests.test_entities_table import TestEntitiesTable
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME
from test_credentials.json_file_credentials import USER_NAME_UNICODE

from axonius.utils.parsing import parse_date_with_timezone
from testing.services.plugins.static_analysis_service import StaticAnalysisService


class TestUsersTable(TestEntitiesTable):
    USER_NAME_COLUMN = 'User Name'
    DOMAIN_COLUMN = 'Domain'
    MAIL_COLUMN = 'Mail'
    ADMIN_COLUMN = 'Is Admin'
    LAST_SEEN_COLUMN = 'Last Seen In Domain'
    ACCOUNT_DISABLED_COLUMN = 'Account Disabled'
    ACCOUNT_LOCKOUT_COLUMN = 'Account Lockout'
    QUERY_FILTER_USERNAME = 'specific_data.data.username == regex("m")'
    QUERY_FIELDS = 'adapters,specific_data.data.image,specific_data.data.username,specific_data.' \
                   'data.domain,specific_data.data.last_seen,specific_data.data.is_admin,labels'

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
        self.users_page.wait_for_table_to_load()
        first_id = self.users_page.find_first_id()
        self.users_page.click_row()
        assert f'users/{first_id}' in self.driver.current_url

    def _test_user_sort_result(self, col_name, desc=True):
        self.users_page.wait_for_spinner_to_end()
        self.users_page.click_sort_column(col_name)
        self.users_page.wait_for_spinner_to_end()
        usernames = self.users_page.get_column_data_slicer(col_name)
        assert len(usernames) > 2

        # Multivalues inside a single entity aren't sorted, let's not test them
        try:
            usernames.remove('avidor\nאבידור')
        except Exception:
            pass
        try:
            usernames.remove('אבידור\navidor')
        except Exception:
            pass

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
        self.users_page.edit_columns(add_col_names=[self.MAIL_COLUMN], remove_col_names=[self.DOMAIN_COLUMN])
        assert len(self.users_page.get_column_data_slicer(self.MAIL_COLUMN))
        with pytest.raises(ValueError):
            # The coloumn is expected to be gone, therefore this throws an exception
            self.users_page.get_column_data_slicer(self.DOMAIN_COLUMN)
        self.users_page.edit_columns(add_col_names=[self.MAIL_COLUMN, self.ACCOUNT_LOCKOUT_COLUMN],
                                     adapter_title=AD_ADAPTER_NAME)

    def test_user_save_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        self.users_page.wait_for_table_to_load()

        self.users_page.customize_view_and_save('test_save_query', 50, self.USER_NAME_COLUMN,
                                                [self.MAIL_COLUMN], [self.DOMAIN_COLUMN],
                                                self.users_page.JSON_ADAPTER_FILTER)
        view_data = self.users_page.get_all_data_proper()

        # Load some default view, to see that the saved one changes it
        self.users_page.execute_saved_query('Users Created in Last 30 Days')
        assert self.users_page.get_all_data_proper() != view_data

        self.users_page.clear_filter()
        self.users_page.execute_saved_query('test_save_query')

        # Check loaded data is equal to original one whose view was saved
        assert self.users_page.get_all_data_proper() == view_data

    def test_users_advanced_basic(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()

        self.check_toggle_advanced_basic(self.users_page, self.users_page.JSON_ADAPTER_FILTER,
                                         self.users_page.ADVANCED_VIEW_RAW_FIELD, self.users_page.FIELD_USERNAME_TITLE)
        self.check_toggle_advanced_basic(self.users_page, self.users_page.AD_ADAPTER_FILTER, 'name:',
                                         self.users_page.FIELD_USERNAME_TITLE)

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

    def _test_column_data_expanded_row(self, col_name):
        merged_data = self.users_page.get_column_data_slicer(col_name)[0].split('\n')
        expanded_data = self.users_page.get_column_data_expand_row(col_name)[0].split('\n')
        assert set(merged_data) == set(expanded_data)

    def test_user_expand_row(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        self.users_page.query_user_name_contains('avidor')
        self.users_page.click_expand_row()
        self.users_page.find_query_search_input().click()

        self._test_column_data_expanded_row(self.USER_NAME_COLUMN)
        self._test_column_data_expanded_row(self.LAST_SEEN_COLUMN)
        self._test_column_data_expanded_row(self.ADMIN_COLUMN)

        adapters = self.users_page.get_column_data_adapter_names()
        merged_adapters = set(adapters[:2])
        expanded_adapters = set(adapters[2:])
        assert merged_adapters == expanded_adapters

    @staticmethod
    def _days_since_date(date_str):
        date_obj = parse_date_with_timezone(date_str, 'Israel').astimezone(pytz.utc).replace(hour=0, minute=0, second=0)
        now_obj = pytz.utc.localize(datetime.utcnow()).replace(hour=0, minute=0, second=0)
        return (now_obj - date_obj).days

    def _test_days_for_last_seen(self, last_seen_date, last_seen_days):
        days = self._days_since_date(last_seen_date)
        assert int(last_seen_days) in (days, days + 1, days + 2)

    def _test_last_seen_expanded_cell(self):
        self.users_page.click_expand_cell(cell_index=self.users_page.count_sort_column(self.LAST_SEEN_COLUMN))
        last_seen_merged = self.users_page.get_column_data_slicer(self.LAST_SEEN_COLUMN)[0].split('\n')
        last_seen_expanded = self.users_page.get_expand_cell_column_data(self.LAST_SEEN_COLUMN, self.LAST_SEEN_COLUMN)
        assert set(last_seen_merged) == set(last_seen_expanded)
        last_seen_expanded_days = self.users_page.get_expand_cell_column_data(self.LAST_SEEN_COLUMN, 'Days')
        self._test_days_for_last_seen(last_seen_expanded[0], last_seen_expanded_days[0])
        if len(last_seen_expanded_days) > 1:
            assert int(last_seen_expanded_days[0]) < int(last_seen_expanded_days[1])
            self._test_days_for_last_seen(last_seen_expanded[1], last_seen_expanded_days[1])
        self.users_page.click_expand_cell(cell_index=self.users_page.count_sort_column(self.LAST_SEEN_COLUMN))
        self.users_page.wait_close_column_details_popup()

    def test_user_expand_cell(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        self.users_page.query_user_name_contains('avidor')
        self.users_page.click_expand_cell(cell_index=self.users_page.count_sort_column(self.USER_NAME_COLUMN))

        user_name_merged = self.users_page.get_column_data_slicer(self.USER_NAME_COLUMN)[0].split('\n')
        user_name_expanded = self.users_page.get_column_data_expand_cell(self.USER_NAME_COLUMN)[0].split('\n')
        assert set(user_name_merged) == set(user_name_expanded)
        self.users_page.click_expand_cell(cell_index=self.users_page.count_sort_column(self.USER_NAME_COLUMN))
        self.users_page.wait_close_column_details_popup()

        self._test_last_seen_expanded_cell()
        self.users_page.query_user_name_contains('ofri')
        self._test_last_seen_expanded_cell()

    def test_user_bool_consistency(self):
        self.settings_page.switch_to_page()
        with StaticAnalysisService().contextmanager(take_ownership=True):
            self.base_page.run_discovery()
            self.users_page.switch_to_page()
            self.users_page.query_user_name_contains('Administrator')
            self.users_page.open_edit_columns()
            self.users_page.add_columns([self.ACCOUNT_DISABLED_COLUMN])
            self.users_page.add_columns([self.ACCOUNT_DISABLED_COLUMN], AD_ADAPTER_NAME)
            self.users_page.close_edit_columns()
            self.users_page.wait_for_table_to_load()
            generic_col_data = self.users_page.get_column_data_slicer(self.ACCOUNT_DISABLED_COLUMN)
            specific_col_data = self.users_page.get_column_data_slicer(self.ACCOUNT_DISABLED_COLUMN, False)
            assert generic_col_data == specific_col_data
