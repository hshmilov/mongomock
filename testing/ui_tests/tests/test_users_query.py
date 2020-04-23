import random
import math

from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import JSON_ADAPTER_NAME, AD_ADAPTER_NAME


class TestUsersQuery(TestBase):
    def test_two_property_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        self.users_page.click_query_wizard()
        self.users_page.add_query_expression()

        expressions = self.users_page.find_expressions()
        assert len(expressions) == 2
        self.users_page.select_query_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.users_page.wait_for_spinner_to_end()
        self.users_page.select_query_logic_op('and')
        self.users_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.users_page.wait_for_spinner_to_end()
        assert self.users_page.count_entities() == 2

    def test_users_query_wizard_default_operators(self):
        self.users_page.switch_to_page()
        self.users_page.wait_for_table_to_load()
        self.users_page.click_query_wizard()
        self.users_page.select_query_adapter(AD_ADAPTER_NAME)
        assert self.users_page.get_query_field() == self.users_page.ID_FIELD
        assert self.users_page.get_query_comp_op() == self.users_page.QUERY_COMP_EXISTS

    def test_over_20_query(self):
        # Do a query that results in more then 20 users (Can use testSecDomain credentials to get more users).
        # Click on "50" users per page and validate number of users displayed
        # Click on last page button (far right ">>"), see that it takes you to last page
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        # Wait for search to return (working so long as there is a spinner)
        self.users_page.wait_for_spinner_to_end()
        real_count = self.axonius_system.get_users_db().count()
        assert len(self.users_page.find_rows_with_data()) == min(20, real_count)
        self.users_page.select_page_size(50)
        assert len(self.users_page.find_rows_with_data()) == real_count

    def test_username_and_adapter_filters_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        self.users_page.click_query_wizard()
        expressions = self.users_page.find_expressions()
        assert len(expressions) == 1
        self.users_page.select_query_field(self.users_page.FIELD_USERNAME_TITLE, parent=expressions[0])
        self.users_page.select_query_comp_op(self.users_page.QUERY_COMP_CONTAINS, parent=expressions[0])
        self.users_page.fill_query_string_value('avi', parent=expressions[0])
        self.users_page.wait_for_spinner_to_end()
        self.users_page.wait_for_table_to_load()
        assert self.users_page.count_entities() == 1
        self.users_page.click_on_select_all_filter_adapters(parent=expressions[0])
        self.users_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        self.users_page.wait_for_spinner_to_end()
        self.users_page.wait_for_table_to_load()

        assert self.users_page.count_entities() == 0

        self.users_page.click_on_select_all_filter_adapters()
        self.users_page.click_on_filter_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.users_page.wait_for_spinner_to_end()
        self.users_page.wait_for_table_to_load()
        assert self.users_page.count_entities() == 1

        self.users_page.fill_query_string_value('ofri', parent=expressions[0])
        self.users_page.wait_for_spinner_to_end()
        self.users_page.wait_for_table_to_load()
        assert self.users_page.count_entities() == 1

        self.users_page.click_on_select_all_filter_adapters()
        self.users_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        self.users_page.wait_for_spinner_to_end()
        self.users_page.wait_for_table_to_load()
        assert self.users_page.count_entities() == 1

    def test_in_integer_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        self.users_page.wait_for_table_to_load()

        self.users_page.edit_columns([self.users_page.FIELD_LOGON_COUNT],
                                     [self.users_page.FIELD_TAGS, self.users_page.FIELD_LAST_SEEN_IN_DOMAIN])
        self.users_page.wait_for_table_to_load()

        all_logon_counts = set(self.users_page.get_column_data_inline_with_remainder(self.users_page.FIELD_LOGON_COUNT))

        logon_counts = random.sample(all_logon_counts, math.ceil(len(all_logon_counts) / 2))

        self.users_page.click_query_wizard()
        self.users_page.select_query_field(self.users_page.FIELD_LOGON_COUNT)
        self.users_page.select_query_comp_op(self.users_page.QUERY_COMP_IN)
        self.users_page.fill_query_string_value(','.join(logon_counts))
        self.users_page.wait_for_table_to_load()
        self.users_page.wait_for_spinner_to_end()

        self.users_page.click_search()

        new_logon_counts = set(self.users_page.get_column_data_inline_with_remainder(
            self.users_page.FIELD_LOGON_COUNT))

        assert len([logon_count for logon_count in new_logon_counts if logon_count.strip() == '']) == 0

        assert set(logon_counts) == new_logon_counts

    def test_active_directory_exists_filtering(self):
        """
        Test that when filtering users who have AD Organizational Unit, we dont get empty result in the field
        """
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        self.users_page.wait_for_table_to_load()
        self.users_page.click_query_wizard()
        self.users_page.select_query_adapter(AD_ADAPTER_NAME)
        self.users_page.select_query_field(self.users_page.AD_ORGANIZATIONAL_UNIT_FIELD)
        self.users_page.select_query_comp_op(self.users_page.QUERY_COMP_EXISTS)
        self.users_page.click_search()
        self.users_page.wait_for_table_to_be_responsive()
        self.users_page.edit_columns(add_col_names=[self.users_page.AD_ORGANIZATIONAL_UNIT_COLUMN])
        cell_index = self.users_page.count_sort_column(self.users_page.AD_ORGANIZATIONAL_UNIT_COLUMN)
        page_size = int(self.users_page.find_active_page_size())
        row_index = 0
        page_index = 4  # Represents the second page.. and so on..
        for index in range(1, self.users_page.count_entities() + 1):
            # If we reached the end of the page, we need to switch to the next one
            if index == page_size:
                row_index = 0
                self.users_page.select_pagination_index(page_index)
                page_index += 1
            row_index += 1
            organizational_unit = self.users_page.get_row_cell_text(row_index, cell_index)
            assert organizational_unit != ''
