from services.plugins.general_info_service import GeneralInfoService
from ui_tests.tests.ui_consts import WMI_INFO_ADAPTER
from ui_tests.tests.ui_test_base import TestBase


class TestEntitiesTable(TestBase):

    @staticmethod
    def check_toggle_advanced_basic(entities_page, entities_filter, expected_advanced_text, expected_basic_text):
        entities_page.switch_to_page()
        entities_page.fill_filter(entities_filter)
        entities_page.enter_search()
        entities_page.wait_for_table_to_load()
        entities_page.click_row()
        entities_page.wait_for_spinner_to_end()
        entities_page.click_advanced_view()
        assert entities_page.find_element_by_text(expected_advanced_text)
        entities_page.click_basic_view()
        assert entities_page.find_element_by_text(expected_basic_text)

    def test_WMI_info_shown(self):
        self.enforcements_page.switch_to_page()
        with GeneralInfoService().contextmanager(take_ownership=True):
            self.enforcements_page.create_run_wmi_scan_on_each_cycle_enforcement()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.click_query_wizard()
            adapters = self.devices_page.get_query_adapters_list()
            # WMI Info should be in the adapters list because its does have a client
            assert WMI_INFO_ADAPTER in adapters
