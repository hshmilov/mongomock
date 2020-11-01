from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import COMP_EXISTS, COMP_EQUALS
from test_credentials.test_orca_credentials_mock import orca_json_file_mock_devices


class TestVulnerabilities(TestBase):
    VULNERABILITY_TO_SEARCH = 'CVE-2015-2716'
    MOCK_DEVICE_ASSET_NAME = 'Web-Nginx'

    def test_device_vulnerabilities(self):
        self.adapters_page.add_json_server(orca_json_file_mock_devices, run_discovery_at_last=False)
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        # Filter the devices table so that only the single device from the above mock would appear
        self.devices_page.build_query(self.devices_page.FIELD_VULNERABLE_SOFTWARE, '', COMP_EXISTS)
        self.devices_page.click_query_wizard()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        self.devices_page.select_query_field(self.devices_page.FIELD_ASSET_NAME, parent=expressions[1])
        self.devices_page.select_query_comp_op(COMP_EQUALS, parent=expressions[1])
        self.devices_page.fill_query_string_value(self.MOCK_DEVICE_ASSET_NAME, parent=expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.close_dropdown()
        # Assert that the mock record has been found and contains vulnerable software
        assert self.devices_page.get_table_count() == 1
        self.devices_page.click_row()
        self.devices_page.click_general_tab()
        self.devices_page.click_vulnerable_software_tab()
        # Check for the existence of cve vulnerability by the cve
        self.devices_page.fill_enter_table_search(self.VULNERABILITY_TO_SEARCH)
        assert self.devices_page.get_table_count() == 1
        self.adapters_page.remove_json_extra_server(orca_json_file_mock_devices)
