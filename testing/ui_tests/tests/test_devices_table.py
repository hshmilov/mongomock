import time
from flaky import flaky

from ui_tests.tests.ui_test_base import TestBase
from axonius.entities import EntityType
from test_credentials.json_file_credentials import DEVICE_FIRST_IP, DEVICE_SECOND_IP


class TestDevicesTable(TestBase):
    LABELS_TEXTBOX_TEXT = 'foobar'
    DELETE_DIALOG_TEXT = 'You are about to delete 1 devices, 1 total adapter devices.'

    @flaky(max_runs=2)
    def test_devices_action_add_and_remove_tag(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.driver.get(self.driver.current_url)
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row_checkbox()
        self.devices_page.add_new_tag(self.LABELS_TEXTBOX_TEXT)
        assert self.devices_page.get_first_tag_text() == self.LABELS_TEXTBOX_TEXT
        self.devices_page.remove_first_tag()
        assert self.devices_page.get_first_tag_text() == ''

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
        assert self.DELETE_DIALOG_TEXT in self.devices_page.read_delete_dialog()
        self.devices_page.confirm_delete()
        self.devices_page.wait_for_element_absent_by_css(self.devices_page.MODAL_OVERLAY_CSS)
        assert not self.devices_page.count_entities()
