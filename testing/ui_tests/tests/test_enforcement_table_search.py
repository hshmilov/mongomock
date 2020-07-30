from ui_tests.tests.enforcement_config_base import TestEnforcementConfigBase
from ui_tests.tests.ui_consts import MANAGED_DEVICES_QUERY_NAME


class TestEnforcementTableSearch(TestEnforcementConfigBase):
    def test_enforcement_table_search(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        enforcement_names = ['Test 3', 'Test 2', 'Test 5', 'Test 1', 'Test 4']
        enforcement_queries = [MANAGED_DEVICES_QUERY_NAME, self.ENFORCEMENT_CHANGE_NAME, MANAGED_DEVICES_QUERY_NAME,
                               self.ENFORCEMENT_CHANGE_NAME, self.ENFORCEMENT_CHANGE_NAME]
        for i, name in enumerate(enforcement_names):
            self.enforcements_page.create_notifying_enforcement(name, enforcement_queries[i])

        self.enforcements_page.fill_enter_table_search('Test')
        self.enforcements_page.wait_for_table_to_load()
        assert len(self.enforcements_page.get_column_data_inline(self.FIELD_NAME)) == 5
        self.enforcements_page.fill_enter_table_search('1')
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_NAME) == ['Test 1']
        self.enforcements_page.fill_enter_table_search(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_QUERY_NAME) == 3 * [
            self.ENFORCEMENT_CHANGE_NAME]
