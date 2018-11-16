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
