import time

import pytest

from axonius.utils.wait import wait_until
from services.adapters.stresstest_service import StresstestService
from ui_tests.tests.ui_consts import (STRESSTEST_ADAPTER,
                                      STRESSTEST_ADAPTER_NAME,
                                      JSON_ADAPTER_NAME)
from ui_tests.tests.ui_test_base import TestBase
from test_credentials.test_cisco_credentials import cisco_json_file_mock_credentials


class TestHyperlinks(TestBase):
    def test_hyperlinks_stresstest(self):
        self.settings_page.switch_to_page()
        with StresstestService().contextmanager(take_ownership=True):
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_adapter(STRESSTEST_ADAPTER_NAME)
            self.adapters_page.click_adapter(STRESSTEST_ADAPTER_NAME)
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
            self.devices_page.fill_filter(f'adapters == \'{STRESSTEST_ADAPTER}\'')
            self.devices_page.enter_search()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_row()
            self.devices_page.wait_for_spinner_to_end()
            # scroll down
            element = self.devices_page.driver.find_element_by_css_selector('[for=test2_hyperlinks_int]')
            self.devices_page.scroll_into_view(element, '[role=tabpanel].stresstest_adapter_0_asd-0>.x-list')

            hyperlinks_str_element = self.devices_page.driver.find_element_by_css_selector(
                '[for=test_hyperlinks_str] + a')
            assert hyperlinks_str_element.text == 'seven'
            assert hyperlinks_str_element.get_property('href') == 'http://test_hyperlinks_str_seven/'

            hyperlinks_str_element = self.devices_page.driver.find_element_by_css_selector(
                '[for=test_hyperlinks_int] + a')
            assert hyperlinks_str_element.text == '7'
            assert hyperlinks_str_element.get_property('href') == 'http://test_hyperlinks_int_7/'

            # Now testing hyperlinks that jump to filter
            hyperlinks_str_element = self.devices_page.driver.find_element_by_css_selector(
                '[for=test2_hyperlinks_str] + a')
            assert hyperlinks_str_element.text == 'fourteen'

            hyperlinks_str_element = self.devices_page.driver.find_element_by_css_selector(
                '[for=test2_hyperlinks_int] + a')
            assert hyperlinks_str_element.text == '14'
            hyperlinks_str_element.click()
            self.devices_page.wait_for_table_to_load()

            # assert that the query is correct
            assert self.devices_page.find_query_search_input().get_attribute('value') ==\
                'adapters_data.stresstest_adapter.test2_hyperlinks_int == 14'

            # assert that the filter works
            assert self.devices_page.count_entities() == 1

    def test_default_values(self):
        clients_db = None
        self.settings_page.switch_to_page()
        try:
            with StresstestService().contextmanager(take_ownership=True) as service:
                clients_db = service.self_database['clients']
                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_adapter(STRESSTEST_ADAPTER_NAME)
                self.adapters_page.click_adapter(STRESSTEST_ADAPTER_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.adapters_page.fill_creds(**{
                    'device_count': 1,
                    'name': 'testing default value'
                })
                self.adapters_page.click_save()
                self.adapters_page.wait_for_spinner_to_end()
                for position in (1, 2):
                    self.adapters_page.wait_for_server_green(position=position, retries=700)

                time.sleep(3)
                clients = clients_db.find({}, limit=3)
                found = False
                for client in clients:
                    client_config = client['client_config']
                    # decrypt client config and check it.
                    service.decrypt_dict(client_config)
                    if client_config['name'] == 'testing default value':
                        assert {
                            'default': 5,
                            'device_count': 1,
                            'name': 'testing default value'
                        }.items() == client_config.items()
                        found = True
                assert found

                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_adapter(STRESSTEST_ADAPTER_NAME)
                self.adapters_page.click_adapter(STRESSTEST_ADAPTER_NAME)
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
                clients = clients_db.find({}, limit=3)
                found = False
                for client in clients:
                    # decrypt client config and check it.
                    client_config = client['client_config']
                    service.decrypt_dict(client_config)
                    if client_config['name'] == 'lol lol lol':
                        assert {
                            'device_count': 2,
                            'name': 'lol lol lol',
                            'default': 10
                        }.items() == client_config.items()
                        found = True
                assert found
        finally:
            if clients_db:
                clients_db.delete_many({})

    @pytest.mark.skip('AX-6869')
    def test_entity_field_links(self):
        self.enforcements_page.switch_to_page()
        self.adapters_page.connect_adapter(JSON_ADAPTER_NAME, cisco_json_file_mock_credentials)
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()

        # Test Aggregated/General Data Advanced tables links
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_CONNECTED_DEVICES)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS)
        self.devices_page.click_search()
        self.devices_page.wait_for_table_to_load()
        link = self.devices_page.find_general_data_table_link(self.devices_page.FIELD_CONNECTED_DEVICES)
        link_text = link.text
        link.click()
        self.devices_page.wait_for_table_to_load()
        ips_column_data = self.devices_page.get_column_data_slicer(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        assert ips_column_data and link_text in ips_column_data[0]

        # Test Aggregated/General Data Basic Info links
        self.devices_page.switch_to_page()
        self.devices_page.run_filter_query(self.devices_page.JSON_ADAPTER_FILTER)
        link = self.devices_page.find_general_data_basic_link(self.devices_page.FIELD_LAST_USED_USERS)
        link_text = link.text
        link.click()
        self.users_page.wait_for_table_to_load()
        time.sleep(5)
        wait_until(lambda: self.users_page.get_column_data_slicer(self.users_page.FIELD_USERNAME_TITLE),
                   tolerated_exceptions_list=[ValueError], check_return_value=False)
        column_data = self.users_page.get_column_data_slicer(self.users_page.FIELD_USERNAME_TITLE)
        assert link_text in column_data, f'link_text: {link_text}, column_data: {column_data}'
        self.adapters_page.remove_json_extra_server(cisco_json_file_mock_credentials)
