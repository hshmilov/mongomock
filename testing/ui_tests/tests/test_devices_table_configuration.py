import time

from axonius.entities import EntityType
from axonius.utils.wait import wait_until
from services.adapters.wmi_service import WmiService
from test_credentials.json_file_credentials import (DEVICE_FIRST_IP,
                                                    DEVICE_SECOND_IP,
                                                    DEVICE_SUBNET)
from ui_tests.tests.test_entities_table import TestEntitiesTable
from ui_tests.tests.ui_consts import (TAG_NAME,
                                      AD_ADAPTER_NAME, WMI_ADAPTER_NAME, JSON_ADAPTER_NAME,
                                      COMP_EXISTS, COMP_CONTAINS, COMP_EQUALS, COMP_SUBNET, LOGIC_AND,
                                      JSON_ADAPTER_FILTER)


class TestDevicesTableMoreCases(TestEntitiesTable):
    def _update_device_field(self, field_name, from_value, to_value):
        self.axonius_system.db.get_entity_db(EntityType.Devices).update_one({
            f'adapters.data.{field_name}': from_value
        }, {
            '$set': {
                f'adapters.$.data.{field_name}': to_value
            }
        })

    def _get_first_hostname(self):
        return self.devices_page.get_column_data_slicer(self.devices_page.FIELD_HOSTNAME_TITLE)[0]

    def test_devices_data_consistency(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()

        initial_value = wait_until(self._get_first_hostname, tolerated_exceptions_list=[IndexError, ValueError])
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
        all_ips = self.devices_page.get_column_data_slicer(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        assert len(all_ips) == 1
        assert all_ips[0] == f'{DEVICE_FIRST_IP}\n{DEVICE_SECOND_IP}\n+1'

    def test_devices_config(self):
        with WmiService().contextmanager(take_ownership=True):
            self.enforcements_page.create_run_wmi_scan_on_each_cycle_enforcement()
            self.base_page.run_discovery()

            # Testing regular Adapter
            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(JSON_ADAPTER_FILTER)
            self.devices_page.enter_search()
            self.devices_page.wait_for_table_to_load()
            first_id = self.devices_page.find_first_id()
            self.devices_page.click_row()
            assert f'devices/{first_id}' in self.driver.current_url
            self.devices_page.wait_for_spinner_to_end()
            self.devices_page.click_adapters_tab()
            assert len(self.devices_page.find_vertical_tabs()) == 2
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_NETWORK_INTERFACES)
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_AVSTATUS)
            self.devices_page.click_general_tab()
            assert self.devices_page.find_vertical_tabs() == ['Basic Info', 'Network Interfaces']
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_ASSET_NAME)
            assert len(self.devices_page.find_elements_by_text(self.devices_page.FIELD_AVSTATUS)) == 0
            self.devices_page.click_tab(self.devices_page.FIELD_TAGS)
            self.devices_page.open_edit_tags()
            self.devices_page.create_save_tags([TAG_NAME])
            self.devices_page.wait_for_spinner_to_end()
            assert self.devices_page.find_element_by_text(TAG_NAME).is_displayed()
            self.devices_page.switch_to_page()
            assert TAG_NAME in self.devices_page.get_column_data_slicer(self.devices_page.FIELD_TAGS)

            # Testing AD Adapter
            self.devices_page.fill_filter(self.devices_page.AD_WMI_ADAPTER_FILTER)
            self.devices_page.enter_search()
            self.devices_page.wait_for_table_to_load()
            wait_until(self.devices_page.get_all_data, total_timeout=60 * 25)
            first_id = self.devices_page.find_first_id()
            self.devices_page.click_row()
            assert f'devices/{first_id}' in self.driver.current_url
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_adapters_tab()
            assert self.devices_page.find_vertical_tabs() == [AD_ADAPTER_NAME,
                                                              WMI_ADAPTER_NAME,
                                                              'Custom Data']
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_NETWORK_INTERFACES)
            self.devices_page.click_tab(AD_ADAPTER_NAME)
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_AD_NAME)

            def _check_installed_software():
                # If it causes blank pages, we need to remove this and find and alternative (long wait before this)
                self.driver.refresh()
                self.devices_page.wait_for_table_to_load()
                self.devices_page.click_general_tab()
                return 'Installed Software' in self.devices_page.find_vertical_tabs()

            wait_until(_check_installed_software, check_return_value=True, total_timeout=60 * 3)

    def test_devices_advanced_basic(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()

        self.check_toggle_advanced_basic(self.devices_page, JSON_ADAPTER_FILTER,
                                         JSON_ADAPTER_NAME, self.devices_page.ADVANCED_VIEW_RAW_FIELD,
                                         self.devices_page.FIELD_ASSET_NAME)

        self.check_toggle_advanced_basic(self.devices_page, self.devices_page.AD_ADAPTER_FILTER, AD_ADAPTER_NAME, 'cn:',
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
        self.devices_page.select_query_comp_op(COMP_SUBNET, expressions[0])
        self.devices_page.fill_query_string_value(DEVICE_SUBNET, expressions[0])
        self.devices_page.select_query_logic_op(LOGIC_AND, expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, expressions[1])
        self.devices_page.select_query_comp_op(COMP_CONTAINS, expressions[1])
        self.devices_page.fill_query_string_value('st', expressions[1])
        self.devices_page.select_query_logic_op(LOGIC_AND, expressions[2])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_SUBNETS, expressions[2])
        self.devices_page.select_query_comp_op(COMP_EQUALS, expressions[2])
        self.devices_page.fill_query_string_value(DEVICE_SUBNET, expressions[2])
        self.devices_page.select_query_logic_op(LOGIC_AND, expressions[3])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_MAC, expressions[3])
        self.devices_page.select_query_comp_op(COMP_EXISTS, expressions[3])
        self.devices_page.wait_for_table_to_load()
        self.devices_page.wait_for_spinner_to_end()
        assert len(self.devices_page.get_all_data()) == 1

    def test_dropdown_columns_text_wrap(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.open_edit_columns()

        adapters_from_edit_columns = self.devices_page.get_edit_columns_adapters_elements()

        if adapters_from_edit_columns is not None and len(adapters_from_edit_columns) > 0:
            first_element_height = adapters_from_edit_columns[0].value_of_css_property('height')
            adapters_from_edit_columns.pop(0)
            for adapter_element in adapters_from_edit_columns:
                assert first_element_height == adapter_element.value_of_css_property('height')

    def test_devices_initial_column_order(self):
        """
        Test that the initial column order of the devices table columns
        is the same as the default fields order
        """
        self.check_initial_column_order(self.devices_page)
