from ui_tests.tests.ui_test_base import TestBase

AZURE_AD_ADAPTER_NAME = 'Microsoft Active Directory (AD)'


class TestDevice(TestBase):
    """
    Device page (i.e view on a single device) related tests
    """

    def test_add_predefined_fields_on_device(self):
        """
        Tests that we can more than one predefined fields on a device
        Actions:
            - Go to device page
            - Select a device
            - Got to custom data tab
            - Press edit fields
            - Add predefined field & Save
                - Verify field was added
            - Create another predefined field & Save
                - Verify new data also exists
        """
        # === Step 1 === #
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        # === Step 2 === #
        self.devices_page.switch_to_page()
        self.devices_page.click_row()
        self.devices_page.click_custom_data_tab()
        self.devices_page.click_custom_data_edit()
        self.devices_page.click_custom_data_add_predefined()
        parent = self.devices_page.find_custom_fields_items()[-1]
        self.devices_page.select_custom_data_field(self.devices_page.FIELD_ASSET_NAME, parent=parent)
        self.devices_page.fill_custom_data_value('DeanSysman', parent=parent, input_type_string=True)
        self.devices_page.save_custom_data()
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.find_element_by_text(self.devices_page.FIELD_ASSET_NAME) is not None
        assert self.devices_page.find_element_by_text('DeanSysman') is not None
        self.devices_page.click_custom_data_edit()
        self.devices_page.click_custom_data_add_predefined()
        parent = self.devices_page.find_custom_fields_items()[-1]
        self.devices_page.select_custom_data_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=parent)
        self.devices_page.fill_custom_data_value('DeanSysman2', parent=parent, input_type_string=True)
        self.devices_page.save_custom_data()
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.find_element_by_text(self.devices_page.FIELD_ASSET_NAME) is not None
        assert self.devices_page.find_element_by_text('DeanSysman2') is not None
