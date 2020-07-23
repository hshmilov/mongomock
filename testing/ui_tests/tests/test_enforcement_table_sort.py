import time

from ui_tests.tests.enforcement_config_base import TestEnforcementConfigBase
from ui_tests.tests.ui_consts import MANAGED_DEVICES_QUERY_NAME


class TestEnforcementTableSort(TestEnforcementConfigBase):

    def test_enforcement_table_sort(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        enforcement_names = ['Test 3', 'Test 2', 'Test 5', 'Test 1', 'Test 4']
        enforcement_queries = [MANAGED_DEVICES_QUERY_NAME, self.ENFORCEMENT_CHANGE_NAME, MANAGED_DEVICES_QUERY_NAME,
                               self.ENFORCEMENT_CHANGE_NAME, self.ENFORCEMENT_CHANGE_NAME]
        for i, name in enumerate(enforcement_names):
            self.enforcements_page.create_notifying_enforcement(name, enforcement_queries[i])

        self.enforcements_page.click_sort_column(self.FIELD_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_NAME) == sorted(enforcement_names, reverse=True)
        self.enforcements_page.click_sort_column(self.FIELD_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_NAME) == sorted(enforcement_names)
        self.enforcements_page.click_sort_column(self.FIELD_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_NAME) == list(reversed(enforcement_names))

        self.enforcements_page.click_sort_column(self.FIELD_QUERY_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(
            self.FIELD_QUERY_NAME) == sorted(enforcement_queries, reverse=True)
        self.enforcements_page.click_sort_column(self.FIELD_QUERY_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_QUERY_NAME) == sorted(enforcement_queries)
        self.enforcements_page.click_sort_column(self.FIELD_QUERY_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(
            self.FIELD_QUERY_NAME) == list(reversed(enforcement_queries))

        # Default sort is according to update time
        for name in sorted(enforcement_names):
            self.enforcements_page.click_enforcement(name)
            self.enforcements_page.click_save_button()
            self.enforcements_page.wait_for_table_to_load()
            # Make a distinct difference between each save
            time.sleep(1)
        assert self.enforcements_page.get_column_data_inline(self.FIELD_NAME) == sorted(enforcement_names, reverse=True)
