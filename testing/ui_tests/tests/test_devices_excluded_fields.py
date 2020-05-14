import pytest
from selenium.common.exceptions import NoSuchElementException

from services.adapters.json_file_service import JsonFileService
from test_credentials.test_gui_credentials import AXONIUS_USER, AXONIUS_RO_USER
from test_credentials.test_esx_credentials import esx_json_file_mock_devices
from ui_tests.tests.test_adapters import JSON_NAME
from ui_tests.tests.ui_consts import JSON_ADAPTER_PLUGIN_NAME
from ui_tests.tests.ui_test_base import TestBase

CORRELATION_REASONS_TITLE = 'Correlation Reasons'


class TestDevicesExcludedFields(TestBase):
    def test_correlation_reasons_not_shown_to_user(self):
        with JsonFileService().contextmanager(take_ownership=True):
            self.adapters_page.add_server(esx_json_file_mock_devices, JSON_NAME)
            self.base_page.run_discovery()

            self.devices_page.switch_to_page()
            with pytest.raises(NoSuchElementException):
                # Make sure cant add as column
                self.devices_page.edit_columns(add_col_names=[CORRELATION_REASONS_TITLE])
            self.devices_page.safe_refresh()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_query_wizard()
            with pytest.raises(NoSuchElementException):
                # Make sure cant select as query field
                self.devices_page.select_query_field(CORRELATION_REASONS_TITLE)

            self.devices_page.safe_refresh()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_row()
            self.devices_page.click_general_tab()

            with pytest.raises(NoSuchElementException):
                # Make sure not shown in device data
                self.devices_page.find_element_by_text(CORRELATION_REASONS_TITLE)

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login(username=AXONIUS_RO_USER['user_name'], password=AXONIUS_RO_USER['password'])

            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_row()
            self.devices_page.click_general_tab()
            # Only _axonius user should be able to see that field
            assert self.devices_page.find_element_by_text(CORRELATION_REASONS_TITLE)

            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])

            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_row()
            self.devices_page.click_general_tab()
            # Only _axonius user should be able to see that field
            assert self.devices_page.find_element_by_text(CORRELATION_REASONS_TITLE)
            self.adapters_page.clean_adapter_servers(JSON_NAME, delete_associated_entities=True)
        self.wait_for_adapter_down(JSON_ADAPTER_PLUGIN_NAME)
