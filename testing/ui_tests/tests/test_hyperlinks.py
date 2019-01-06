from services.adapters.stresstest_service import StresstestService
from ui_tests.tests.ui_test_base import TestBase


class TestHyperlinks(TestBase):
    def test_hyperlinks_stresstest(self):
        stresstest_name = 'stresstest_adapter'

        self.settings_page.switch_to_page()
        with StresstestService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(stresstest_name)
            self.adapters_page.click_adapter(stresstest_name)
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.click_new_server()
            self.adapters_page.fill_creds(**{
                'device_count': 1,
                'name': 'asd'
            })
            self.adapters_page.click_save()
            self.adapters_page.wait_for_spinner_to_end()

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(f'adapters == \'{stresstest_name}\'')
            self.devices_page.enter_search()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_row()
            self.devices_page.wait_for_spinner_to_end()
            # scroll down
            element = self.devices_page.driver.find_element_by_css_selector('[for=test2_hyperlinks_int]')
            self.devices_page.scroll_into_view(element, '[role=tabpanel].stresstest_adapter_0_asd-0>.x-list')

            hyperlinks_str_element = self.devices_page.driver.find_element_by_css_selector(
                '[for=test_hyperlinks_str]+div>a')
            assert hyperlinks_str_element.text == 'seven'
            assert hyperlinks_str_element.get_property('href') == 'http://test_hyperlinks_str_seven/'

            hyperlinks_str_element = self.devices_page.driver.find_element_by_css_selector(
                '[for=test_hyperlinks_int]+div>a')
            assert hyperlinks_str_element.text == '7'
            assert hyperlinks_str_element.get_property('href') == 'http://test_hyperlinks_int_7/'

            # Now testing hyperlinks that jump to filter
            hyperlinks_str_element = self.devices_page.driver.find_element_by_css_selector(
                '[for=test2_hyperlinks_str]+div>a')
            assert hyperlinks_str_element.text == 'fourteen'

            hyperlinks_str_element = self.devices_page.driver.find_element_by_css_selector(
                '[for=test2_hyperlinks_int]+div>a')
            assert hyperlinks_str_element.text == '14'
            hyperlinks_str_element.click()
            self.devices_page.wait_for_table_to_load()

            # assert that the query is correct
            assert self.devices_page.find_query_search_input().get_attribute('value') ==\
                'adapters_data.stresstest_adapter.test2_hyperlinks_int == 14'

            # assert that the filter works
            assert self.devices_page.count_entities() == 1
