import pytest
from selenium.common.exceptions import NoSuchElementException

from ui_tests.tests.ui_consts import SPECIFIC_SEARCH_TYPES
from ui_tests.tests.ui_test_base import TestBase


class TestDevicesSpecificSearch(TestBase):

    SPECIFIC_SEARCH_DROPDOWN_CSS = '.x-search-input'
    SPECIFIC_SEARCH_BADGE_CSS = '.x-search-input .input-badge'
    SPECIFIC_SEARCH_CLOSE_BUTTON_CSS = SPECIFIC_SEARCH_BADGE_CSS + ' .remove-search-type'
    TEST_QUERY_NAME = 'testonius'
    TEST_QUERY_EXPRESSION = '(specific_data.data.network_interfaces.ips == regex(\'10\', \'i\'))'
    BUILD_ASSET_QUERY_EXPRESSION = '(specific_data.data.name == regex("cb", "i"))'
    TEST_QUERY_EXPRESSION_WIN = '(specific_data.data.hostname == regex(\'win\', \'i\'))'
    DEFAULT_PLACEHOLDER = 'Insert your query or start typing to filter recent queries'
    SPECIFIC_SEARCH_PLACEHOLDER = 'Search by {search_name}'
    REGULAR_SEARCH_VALUE = 'win'
    IP_ADDRESS_SEARCH_TYPE = 'IP Address'
    INSTALLED_SOFTWARE_NAME_SEARCH_TYPE = 'Installed Software Name'

    @pytest.mark.skip('ad change')
    def test_specific_search_query(self):
        self.base_page.wait_for_run_research()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.select_specific_search(self.devices_page.FIELD_HOSTNAME_TITLE)
        self.devices_page.search(self.REGULAR_SEARCH_VALUE)
        self.devices_page.check_search_text_result_in_column(self.REGULAR_SEARCH_VALUE,
                                                             self.devices_page.FIELD_HOSTNAME_TITLE)
        result_count = self.devices_page.get_table_count()
        assert result_count == 10
        self.devices_page.close_specific_search_badge()
        self.devices_page.wait_for_table_to_load()
        # check result are different now, the query restarted
        assert result_count != self.devices_page.get_table_count()

    def test_specific_search_sanity(self):
        self.devices_page.switch_to_page()
        for search_key, search_name in SPECIFIC_SEARCH_TYPES.items():
            self.devices_page.select_specific_search(search_name)
            assert self.devices_page.find_specific_search_badge()
            search_input_placeholder = self.devices_page.get_query_search_input_attribute('placeholder')
            assert search_input_placeholder == self.SPECIFIC_SEARCH_PLACEHOLDER.format(
                search_name=search_name)
            self.devices_page.open_edit_columns()
            assert self.devices_page.find_save_as_user_search_default_button(search_name=search_name)
            self.devices_page.close_edit_columns()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.open_columns_menu()
            assert self.devices_page.find_reset_columns_to_user_default_button(search=True)
            assert self.devices_page.find_reset_columns_to_system_default_button(search=True)
            self.devices_page.close_specific_search_badge()
            self.devices_page.wait_for_table_to_load()

        # check back to normal texts
        search_input_placeholder = self.devices_page.get_query_search_input_attribute('placeholder')
        assert search_input_placeholder == self.DEFAULT_PLACEHOLDER
        self.devices_page.open_edit_columns()
        assert self.devices_page.find_save_as_user_search_default_button()
        self.devices_page.close_edit_columns()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.open_columns_menu()
        assert self.devices_page.find_reset_columns_to_user_default_button()
        assert self.devices_page.find_reset_columns_to_system_default_button()

    def test_specific_search_user_defined_columns(self):
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        base_columns = self.devices_page.get_columns_header_text()
        self.devices_page.select_specific_search(self.devices_page.FIELD_LAST_USED_USERS)
        specific_columns = self.devices_page.get_columns_header_text()
        self.devices_page.reset_columns_system_default()
        assert specific_columns == self.devices_page.get_columns_header_text()
        self.devices_page.reset_columns_user_default()
        assert specific_columns == self.devices_page.get_columns_header_text()
        self.devices_page.open_edit_columns()
        self.devices_page.remove_columns([self.devices_page.FIELD_TAGS,
                                          self.devices_page.FIELD_HOSTNAME_TITLE])
        # save as user default
        self.devices_page.close_edit_columns_save_default(specific_search_name=self.devices_page.FIELD_LAST_USED_USERS)
        self.devices_page.wait_for_table_to_be_responsive()
        # assert diff current specific
        assert not specific_columns == self.devices_page.get_columns_header_text()
        new_specific_columns = self.devices_page.get_columns_header_text()
        self.devices_page.reset_columns_system_default()
        assert specific_columns == self.devices_page.get_columns_header_text()
        self.devices_page.reset_columns_user_default()
        assert new_specific_columns == self.devices_page.get_columns_header_text()
        # reset from header
        self.devices_page.reset_query()
        assert base_columns == self.devices_page.get_columns_header_text()

    def test_specific_search_save_to_saved_query(self):
        self.base_page.wait_for_run_research()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.select_specific_search(self.IP_ADDRESS_SEARCH_TYPE)
        self.devices_page.search('10')
        self.devices_page.save_query_as(self.TEST_QUERY_NAME)
        self.devices_page.check_search_text_result_in_column('10', self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        assert self.devices_page.find_search_value() == self.TEST_QUERY_EXPRESSION
        self.devices_page.reset_query()
        self.devices_page.execute_saved_query(self.TEST_QUERY_NAME)
        self.devices_page.check_search_text_result_in_column('10', self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        assert self.devices_page.find_search_value() == self.TEST_QUERY_EXPRESSION

    def test_specific_search_reset_from_query_wizard(self):
        self.devices_page.switch_to_page()
        self.devices_page.select_specific_search(self.INSTALLED_SOFTWARE_NAME_SEARCH_TYPE)
        self.devices_page.fill_filter('chrome')
        self.devices_page.click_query_wizard()
        self.devices_page.clear_query_wizard()
        self.devices_page.close_dropdown()
        self._check_no_search_template_apply()
        self.devices_page.select_specific_search(self.INSTALLED_SOFTWARE_NAME_SEARCH_TYPE)
        self.devices_page.fill_filter('chrome')
        self.devices_page.enter_search()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.build_query(self.devices_page.FIELD_ASSET_NAME,
                                      'cb',
                                      self.devices_page.QUERY_COMP_CONTAINS)
        self._check_no_search_template_apply()

    @pytest.mark.skip('ad change')
    def test_specific_search_input_value_behaviour(self):
        self.base_page.wait_for_run_research()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.search(self.REGULAR_SEARCH_VALUE)
        self._check_input_value_and_results_count(8, self.REGULAR_SEARCH_VALUE)
        self.devices_page.search('wind')
        self._check_input_value_and_results_count(0, 'wind')
        self._reset_search()
        self.devices_page.search(self.REGULAR_SEARCH_VALUE)
        self.devices_page.select_specific_search(self.devices_page.FIELD_HOSTNAME_TITLE)
        self._check_input_value_and_results_count()
        self.devices_page.search(self.REGULAR_SEARCH_VALUE)
        self._check_input_value_and_results_count(10, self.REGULAR_SEARCH_VALUE)
        self._reset_search()
        self.devices_page.select_specific_search(self.devices_page.FIELD_HOSTNAME_TITLE)
        self.devices_page.search(self.REGULAR_SEARCH_VALUE)
        self.devices_page.save_query_as(self.TEST_QUERY_NAME)
        self._check_input_value_and_results_count(10, self.TEST_QUERY_EXPRESSION_WIN)
        self._reset_search()
        self._check_input_value_and_results_count()
        self.devices_page.execute_saved_query(self.TEST_QUERY_NAME)
        self._check_input_value_and_results_count(10, self.TEST_QUERY_EXPRESSION_WIN)
        self.users_page.switch_to_page()
        self.devices_page.switch_to_page()
        self._check_input_value_and_results_count(10, self.TEST_QUERY_EXPRESSION_WIN)
        self._reset_search()
        self.devices_page.search(self.REGULAR_SEARCH_VALUE)
        self._check_input_value_and_results_count(8, self.REGULAR_SEARCH_VALUE)
        self.users_page.switch_to_page()
        self.devices_page.switch_to_page()
        self._check_input_value_and_results_count(8, self.REGULAR_SEARCH_VALUE)

    def _check_input_value_and_results_count(self, count=22, value=''):
        assert self.devices_page.get_table_count() == count
        assert self.devices_page.find_search_value() == value

    def _reset_search(self):
        self.devices_page.reset_query()
        self.devices_page.wait_for_table_to_load()
        self._check_input_value_and_results_count()

    def _check_no_search_template_apply(self):
        with pytest.raises(NoSuchElementException):
            self.devices_page.find_specific_search_badge()
