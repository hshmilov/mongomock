import time
from services.adapters.stresstest_service import StresstestService
from services.adapters.cisco_service import CiscoService
from ui_tests.tests.ui_test_base import TestBase
from devops.scripts.automate_dev import credentials_inputer


class TestHyperlinks(TestBase):
    def test_hyperlinks_stresstest(self):
        stresstest_name = 'stresstest_adapter'

        self.settings_page.switch_to_page()
        with StresstestService().contextmanager(take_ownership=True):
            self.adapters_page.switch_to_page()
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

    def test_default_values(self):
        stresstest_name = 'stresstest_adapter'

        self.settings_page.switch_to_page()
        try:
            with StresstestService().contextmanager(take_ownership=True) as service:
                clients_db = service.self_database['clients']
                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_adapter(stresstest_name)
                self.adapters_page.click_adapter(stresstest_name)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.adapters_page.fill_creds(**{
                    'device_count': 1,
                    'name': 'testing default value'
                })
                self.adapters_page.click_save()
                self.adapters_page.wait_for_spinner_to_end()
                time.sleep(3)
                assert clients_db.count_documents({
                    'client_config.default': 5,
                    'client_config.device_count': 1,
                    'client_config.name': 'testing default value'
                }, limit=1) == 1

                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_adapter(stresstest_name)
                self.adapters_page.click_adapter(stresstest_name)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()

                self.adapters_page.fill_creds(**{
                    'device_count': 2,
                    'name': 'lol lol lol',
                    'default': 10
                })
                self.adapters_page.click_save()
                self.adapters_page.wait_for_spinner_to_end()
                time.sleep(3)

                assert clients_db.count_documents({
                    'client_config.default': 10,
                    'client_config.device_count': 2,
                    'client_config.name': 'lol lol lol'
                }, limit=1) == 1
        finally:
            clients_db.delete_many({})

    def test_entity_field_links(self):
        self.enforcements_page.switch_to_page()
        with CiscoService().contextmanager(take_ownership=True):
            credentials_inputer.main()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.click_query_wizard()
            self.devices_page.select_query_field(self.devices_page.FIELD_CONNECTED_DEVICES)
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS)
            self.devices_page.click_search()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_row()
            self.devices_page.wait_for_spinner_to_end()
            self.devices_page.click_general_tab()
            self.devices_page.click_tab(self.devices_page.FIELD_CONNECTED_DEVICES)
            link = self.devices_page.driver.find_element_by_css_selector(
                '.x-entity-general .x-tab.active .table-container .x-row td a')
            link_text = link.text
            link.click()
            self.devices_page.wait_for_table_to_load()
            assert link_text in self.devices_page.get_column_data(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
