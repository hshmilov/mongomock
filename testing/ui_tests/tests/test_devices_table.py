import time

from axonius.entities import EntityType
from axonius.utils.wait import wait_until
from services.plugins.general_info_service import GeneralInfoService
from test_credentials.json_file_credentials import (DEVICE_FIRST_IP,
                                                    DEVICE_SECOND_IP)
from ui_tests.tests.ui_test_base import TestBase


class TestDevicesTable(TestBase):
    LABELS_TEXTBOX_TEXT = 'foobar'
    DELETE_DIALOG_TEXT = 'You are about to delete 1 devices, 1 total adapter devices.'

    def test_devices_action_add_and_remove_tag(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        # 'saved queries' button is hiding the first row of the table
        # using a click on the table removes the 'saved queries' from the screen
        self.devices_page.click_sort_column(self.devices_page.FIELD_TAGS)
        self.devices_page.click_row_checkbox()
        self.devices_page.add_new_tag(self.LABELS_TEXTBOX_TEXT)
        assert self.LABELS_TEXTBOX_TEXT in self.devices_page.get_first_row_tags()
        self.devices_page.remove_first_tag()
        assert not self.devices_page.get_first_row_tags()

    def test_devices_action_remove_plugin_tag(self):
        with GeneralInfoService().contextmanager(take_ownership=True):
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_execution_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True)
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            wait_until(lambda: any(self.devices_page.get_column_data(
                self.devices_page.FIELD_TAGS)), total_timeout=60 * 5)
            self.settings_page.switch_to_page()
            self.devices_page.switch_to_page()
            self.devices_page.click_sort_column(self.devices_page.FIELD_TAGS)
            self.devices_page.click_row_checkbox()
            tag_to_remove = self.devices_page.get_first_tag_text()
            self.devices_page.remove_tag(tag_to_remove)
            assert tag_to_remove not in self.devices_page.get_first_row_tags()

    def test_devices_save_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()

        self.devices_page.customize_view_and_save('test_save_query', 50, self.devices_page.FIELD_HOSTNAME_TITLE,
                                                  [self.devices_page.FIELD_LAST_SEEN, self.devices_page.FIELD_OS_TYPE],
                                                  self.devices_page.JSON_ADAPTER_FILTER)
        view_data = self.devices_page.get_all_data()

        # Load some default view, to change it and test the saved view's influence
        self.devices_page.execute_saved_query('Windows Operating System')
        assert self.devices_page.get_all_data() != view_data

        self.devices_page.clear_filter()
        self.devices_page.execute_saved_query('test_save_query')

        # Check loaded data is equal to original one whose view was saved
        assert self.devices_page.get_all_data() == view_data

    def _update_device_field(self, field_name, from_value, to_value):
        self.axonius_system.db.get_entity_db_view(EntityType.Devices).update_one({
            f'specific_data.data.{field_name}': from_value
        }, {
            '$set': {
                f'specific_data.$.data.{field_name}': to_value
            }
        })

    def test_devices_data_consistency(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()

        initial_value = self.devices_page.get_column_data(self.devices_page.FIELD_HOSTNAME_TITLE)[0]
        updated_value = f'{initial_value} improved!'
        self._update_device_field(self.devices_page.FIELD_HOSTNAME_NAME, initial_value, updated_value)
        time.sleep(31)
        assert updated_value == self.devices_page.get_column_data(self.devices_page.FIELD_HOSTNAME_TITLE)[0]

        self._update_device_field(self.devices_page.FIELD_HOSTNAME_NAME, updated_value, initial_value)
        updated_value = f'{initial_value} \\ edited \\\\'
        self._update_device_field(self.devices_page.FIELD_HOSTNAME_NAME, initial_value, updated_value)
        time.sleep(31)
        assert updated_value == self.devices_page.get_column_data(self.devices_page.FIELD_HOSTNAME_TITLE)[0]
        self._update_device_field(self.devices_page.FIELD_HOSTNAME_NAME, updated_value, initial_value)

        self.devices_page.query_json_adapter()
        all_ips = self.devices_page.get_column_data(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        assert len(all_ips) == 1
        assert all_ips[0] == f'{DEVICE_FIRST_IP}\n{DEVICE_SECOND_IP}\n+1'

    def test_devices_delete(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()

        self.devices_page.query_json_adapter()
        self.devices_page.click_row_checkbox()
        self.devices_page.open_delete_dialog()
        wait_until(lambda: self.DELETE_DIALOG_TEXT in self.devices_page.read_delete_dialog())
        self.devices_page.confirm_delete()
        self.devices_page.wait_for_element_absent_by_css(self.devices_page.MODAL_OVERLAY_CSS)
        assert not self.devices_page.count_entities()

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
            assert len(self.devices_page.find_vertical_tabs()) == 1
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_NETWORK_INTERFACES)
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_AVSTATUS)
            self.devices_page.click_tab('General Data')
            assert self.devices_page.find_vertical_tabs() == ['Basic Info']
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
            assert not self.devices_page.find_element_by_text(self.devices_page.FIELD_AVSTATUS).is_displayed()
            self.devices_page.click_tab('Tags')
            assert self.devices_page.find_element_by_text('Edit Tags')

            # Testing AD Adapter
            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(self.devices_page.AD_WMI_ADAPTER_FILTER)
            self.devices_page.enter_search()
            self.devices_page.wait_for_table_to_load()
            wait_until(self.devices_page.get_all_data, total_timeout=60 * 25)
            first_id = self.devices_page.find_first_id()
            self.devices_page.click_row()
            assert f'devices/{first_id}' in self.driver.current_url
            self.devices_page.click_tab('Adapters Data')
            assert self.devices_page.find_vertical_tabs() == ['WMI Info', 'Active Directory']
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_NETWORK_INTERFACES)
            self.devices_page.click_tab('Active Directory')
            assert self.devices_page.find_element_by_text(self.devices_page.FIELD_AD_NAME)
            self.devices_page.click_tab('General Data')
            assert 'Installed Software' in self.devices_page.find_vertical_tabs()

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
