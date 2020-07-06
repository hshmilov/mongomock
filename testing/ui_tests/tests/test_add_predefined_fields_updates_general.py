from ui_tests.tests.device_test_base import TestDeviceBase


class TestAddPredefinedFieldsUpdatesGeneral(TestDeviceBase):
    def test_add_predefined_fields_updates_general(self):
        print('starting test_add_predefined_fields_updates_general', flush=True)
        asset_name = 'asset name 123'
        host_name = 'host name 123'
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.devices_page.click_custom_data_tab()
        self.devices_page.click_custom_data_edit()

        self.devices_page.click_custom_data_add_predefined()
        parent = self.devices_page.find_custom_fields_items()[-1]
        self.devices_page.select_custom_data_field(self.devices_page.FIELD_ASSET_NAME, parent=parent)
        self.devices_page.fill_custom_data_value(asset_name, parent=parent, input_type_string=True)

        self.devices_page.click_custom_data_add_predefined()
        parent = self.devices_page.find_custom_fields_items()[-1]
        self.devices_page.select_custom_data_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=parent)
        self.devices_page.fill_custom_data_value(host_name, parent=parent, input_type_string=True)

        self.devices_page.save_custom_data()
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.safe_refresh()
        self.devices_page.click_general_tab()
        assert self.devices_page.find_element_by_text(self.devices_page.FIELD_ASSET_NAME)
        assert self.devices_page.find_element_by_text(asset_name)

        assert self.devices_page.find_element_by_text(self.devices_page.FIELD_HOSTNAME_TITLE)
        assert self.devices_page.find_element_by_text(host_name)
