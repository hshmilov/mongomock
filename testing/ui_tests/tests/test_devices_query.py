from ui_tests.tests.ui_test_base import TestBase


class TestDevicesQuery(TestBase):
    def test_bad_subnet(self):
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.select_saved_query(self.devices_page.SAVED_QUERY_NETWORK_INTERFACES_IPS)
        self.devices_page.select_query_second_phase('subnet')
        self.devices_page.fill_query_third_phase('1.1.1.1')
        self.devices_page.find_element_by_text('Specify <address>/<CIDR> to filter IP by subnet')
        self.devices_page.click_search()
