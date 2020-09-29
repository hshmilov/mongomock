from ui_tests.tests.ui_test_base import TestBase


class QueryTestBase(TestBase):

    def prepare_to_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.click_query_wizard()
