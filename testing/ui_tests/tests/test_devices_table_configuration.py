import time

from axonius.entities import EntityType
from axonius.utils.wait import wait_until
from services.plugins.general_info_service import GeneralInfoService
from test_credentials.json_file_credentials import (DEVICE_FIRST_IP,
                                                    DEVICE_SECOND_IP,
                                                    DEVICE_SUBNET)
from ui_tests.tests.test_entities_table import TestEntitiesTable
from ui_tests.tests.ui_consts import TAG_NAME


class TestDevicesTable(TestEntitiesTable):
    def _update_device_field(self, field_name, from_value, to_value):
        self.axonius_system.db.get_entity_db(EntityType.Devices).update_one({
            f'adapters.data.{field_name}': from_value
        }, {
            '$set': {
                f'adapters.$.data.{field_name}': to_value
            }
        })

    def _get_first_hostname(self):
        return self.devices_page.get_column_data(self.devices_page.FIELD_HOSTNAME_TITLE)[0]

    def test_devices_data_consistency(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()

        initial_value = wait_until(self._get_first_hostname, exc_list=(IndexError,))
        updated_value = f'{initial_value} improved!'
        self._update_device_field(self.devices_page.FIELD_HOSTNAME_NAME, initial_value, updated_value)
        time.sleep(71)
        assert updated_value == self._get_first_hostname()

        self._update_device_field(self.devices_page.FIELD_HOSTNAME_NAME, updated_value, initial_value)
        updated_value = f'{initial_value} \\ edited \\\\'
        self._update_device_field(self.devices_page.FIELD_HOSTNAME_NAME, initial_value, updated_value)
        time.sleep(71)
        assert updated_value == self._get_first_hostname()
        self._update_device_field(self.devices_page.FIELD_HOSTNAME_NAME, updated_value, initial_value)

        self.devices_page.query_json_adapter()
        all_ips = self.devices_page.get_column_data(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        assert len(all_ips) == 1
        assert all_ips[0] == f'{DEVICE_FIRST_IP}\n{DEVICE_SECOND_IP}\n+1'

    def test_devices_config(self):
        with GeneralInfoService().contextmanager(take_ownership=True):
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            self.settings_page.click_toggle_button(self.settings_page.find_execution_toggle(), make_yes=True)
            self.settings_page.save_and_wait_for_toaster()
            self.base_page.run_discovery()

            # Testing regular Adapter
            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(self.devices_page.JSON_ADAPTER_FILTER)
            self.devices_page.enter_search()
            self.devices_page.wait_for_table_to_load()
            first_id = self.devices_page.find_first_id()
            self.devices_page.click_row()
            assert f'devices/{first_id}' in self.driver.current_url
            self.devices_page.click_tab('Adapters Data')
            assert len(self.devices_page.find_vertical_tabs()) == 2
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_NETWORK_INTERFACES)
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_AVSTATUS)
            self.devices_page.click_tab('General Data')
            assert self.devices_page.find_vertical_tabs() == ['Basic Info', 'Network Interfaces']
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_ASSET_NAME)
            assert not self.devices_page.find_element_by_text(self.devices_page.FIELD_AVSTATUS).is_displayed()
            self.devices_page.click_tab(self.devices_page.FIELD_TAGS)
            self.devices_page.open_edit_tags()
            self.devices_page.create_save_tag(TAG_NAME)
            self.devices_page.wait_for_spinner_to_end()
            assert self.devices_page.find_element_by_text(TAG_NAME).is_displayed()
            self.devices_page.switch_to_page()
            assert TAG_NAME in self.devices_page.get_column_data(self.devices_page.FIELD_TAGS)

            # Testing AD Adapter
            self.devices_page.fill_filter(self.devices_page.AD_WMI_ADAPTER_FILTER)
            self.devices_page.enter_search()
            self.devices_page.wait_for_table_to_load()
            wait_until(self.devices_page.get_all_data, total_timeout=60 * 25)
            first_id = self.devices_page.find_first_id()
            self.devices_page.click_row()
            assert f'devices/{first_id}' in self.driver.current_url
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_tab('Adapters Data')
            assert self.devices_page.find_vertical_tabs() == ['WMI Info', 'Active Directory', 'Custom Data']
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_NETWORK_INTERFACES)
            self.devices_page.click_tab('Active Directory')
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_AD_NAME)

            def _check_installed_software():
                # If it causes blank pages, we need to remove this and find and alternative (long wait before this)
                self.driver.refresh()
                self.devices_page.wait_for_table_to_load()
                self.devices_page.click_tab('General Data')
                return 'Installed Software' in self.devices_page.find_vertical_tabs()

            wait_until(_check_installed_software, check_return_value=True, total_timeout=60 * 3)

    def test_multi_table_and_single_adapter_view(self):
        try:
            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.settings_page.click_gui_settings()
            self.settings_page.wait_for_spinner_to_end()
            self.settings_page.set_single_adapter_checkbox()
            self.settings_page.set_table_multi_line_checkbox()
            self.settings_page.click_save_button()
            self.devices_page.switch_to_page()
            self.devices_page.check_if_table_is_multi_line()
            self.devices_page.click_row()
            # if its not exist than single adapter is working
            self.devices_page.check_if_adapter_tab_not_exist()
        finally:
            self.settings_page.switch_to_page()
            self.settings_page.click_gui_settings()
            self.settings_page.wait_for_spinner_to_end()
            self.settings_page.set_single_adapter_checkbox(make_yes=False)
            self.settings_page.set_table_multi_line_checkbox(make_yes=False)
            self.settings_page.click_save_button()

    def test_devices_advanced_basic(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()

        self.check_toggle_advanced_basic(self.devices_page, self.devices_page.JSON_ADAPTER_FILTER,
                                         self.devices_page.ADVANCED_VIEW_RAW_FIELD, self.devices_page.FIELD_ASSET_NAME)
        self.check_toggle_advanced_basic(self.devices_page, self.devices_page.AD_ADAPTER_FILTER, '"cn":',
                                         self.devices_page.FIELD_HOSTNAME_TITLE)

    def test_table_grey_out(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.fill_filter(self.devices_page.AD_ADAPTER_FILTER)
        self.devices_page.enter_search()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.click_query_wizard()
        for i in range(3):
            self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 4
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS, expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SUBNET, expressions[0])
        self.devices_page.fill_query_value(DEVICE_SUBNET, expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, expressions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, expressions[1])
        self.devices_page.fill_query_value('st', expressions[1])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, expressions[2])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_SUBNETS, expressions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, expressions[2])
        self.devices_page.fill_query_value(DEVICE_SUBNET, expressions[2])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, expressions[3])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_MAC, expressions[3])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, expressions[3])
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) == 1
