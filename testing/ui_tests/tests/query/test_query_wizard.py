from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import DEVICES_SEEN_NEGATIVE_VALUE_QUERY, WINDOWS_QUERY_NAME, JSON_ADAPTER_NAME, \
    COMP_CONTAINS, COMP_EQUALS, COMP_NEXT_DAYS
from test_credentials.test_cisco_credentials import cisco_json_file_mock_credentials


class TestQueryWizard(TestBase):

    def test_query_wizard_negative_values(self):

        self.adapters_page.add_json_server(cisco_json_file_mock_credentials)

        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.add_query_last_seen_negative_value(JSON_ADAPTER_NAME,
                                                             self.devices_page.FIELD_LAST_SEEN,
                                                             COMP_NEXT_DAYS,
                                                             -1)
        current_query = self.devices_page.find_search_value()
        assert DEVICES_SEEN_NEGATIVE_VALUE_QUERY == current_query
        assert self.devices_page.count_entities() == 1

        self.adapters_page.remove_json_extra_server(cisco_json_file_mock_credentials)

    def test_saved_query_change(self):
        #  First, select some other query.
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)

        self.devices_page.click_query_wizard()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(COMP_CONTAINS, parent=expressions[0])
        self.devices_page.fill_query_string_value('test', parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()

        # Select saved query.
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_SAVED_QUERY, parent=expressions[0])
        self.devices_page.select_query_value(WINDOWS_QUERY_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()

    # pylint: disable=anomalous-backslash-in-string
    def test_query_wizard_escape_characters(self):
        self.adapters_page.add_json_server(cisco_json_file_mock_credentials)

        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.click_query_wizard()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1

        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(COMP_CONTAINS, parent=expressions[0])
        self.devices_page.fill_query_string_value('test', parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        query_search_value = self.devices_page.find_search_value()
        assert query_search_value == '(specific_data.data.hostname == regex("test", "i"))'

        self.devices_page.fill_query_string_value('test+special-characters', parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        query_search_value = self.devices_page.find_search_value()
        assert query_search_value == '(specific_data.data.hostname == regex("test\+special\-characters", "i"))'

        self.devices_page.select_query_comp_op(COMP_EQUALS, parent=expressions[0])
        self.devices_page.fill_query_string_value('test+special-characters', parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        query_search_value = self.devices_page.find_search_value()
        assert query_search_value == '(specific_data.data.hostname == "test+special-characters")'

        self.devices_page.select_query_comp_op(COMP_CONTAINS, parent=expressions[0])
        self.devices_page.fill_query_string_value('test+special-characters', parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        query_search_value = self.devices_page.find_search_value()
        assert query_search_value == '(specific_data.data.hostname == regex("test\+special\-characters", "i"))'

    def test_query_wizard_search_disabled(self):
        """
        Checks that the search button in the query wizard gets disabled in case of error.
        Also check that clicking "clear" in the wizard resets the error.
        """
        self._check_query_wizard_search_disabled()
        self.settings_page.disable_auto_querying()
        # we check the same thing but this time with auto querying disabled
        self._check_query_wizard_search_disabled()

    def _check_query_wizard_search_disabled(self):
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE)
        self.devices_page.select_query_comp_op(COMP_EQUALS)
        assert not self.devices_page.is_element_clickable(self.devices_page.get_search_button())
        self.devices_page.fill_query_string_value('random meaningless value')
        assert self.devices_page.is_element_clickable(self.devices_page.get_search_button())
        self.devices_page.fill_query_string_value('')
        assert not self.devices_page.is_element_clickable(self.devices_page.get_search_button())
        self.devices_page.clear_query_wizard()
        assert self.devices_page.is_element_clickable(self.devices_page.get_search_button())
        self.devices_page.click_search()
