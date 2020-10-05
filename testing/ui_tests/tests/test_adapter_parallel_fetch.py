from selenium.common.exceptions import NoSuchElementException

from axonius.utils.wait import wait_until
from services.adapters.cisco_service import CiscoService
from services.adapters.esx_service import EsxService
from test_credentials.test_cisco_credentials import cisco_creds
from test_credentials.test_esx_credentials import client_details as esx_client_details
from test_credentials.test_gui_credentials import AXONIUS_USER
from ui_tests.tests.test_adapters import ESX_NAME
from ui_tests.tests.test_adapters_connections import CISCO_PLUGIN_NAME
from ui_tests.tests.test_enforcement_actions import ESX_PLUGIN_NAME
from ui_tests.tests.ui_test_base import TestBase

CISCO_NAME = 'Cisco'


class TestAdaptersParallelFetch(TestBase):
    def _toggle_parallel_fetch(self, toggle_value):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])

        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.toggle_parallel_fetch(toggle_value)
        self.settings_page.save_and_wait_for_toaster()

    def test_cisco_parallel_fetch(self):
        self.settings_page.switch_to_page()
        self._toggle_parallel_fetch(True)

        self.adapters_page.switch_to_page()
        with CiscoService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(CISCO_NAME)
            self.adapters_page.click_adapter(CISCO_NAME)
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_table_to_be_responsive()
            self.adapters_page.click_new_server()
            self.adapters_page.fill_creds(**cisco_creds)
            self.adapters_page.click_save_and_fetch()
            self.adapters_page.wait_for_spinner_to_end()

            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()
            wait_until(lambda: self.devices_page.get_table_count() > 0,
                       tolerated_exceptions_list=[NoSuchElementException])
            self.adapters_page.clean_adapter_servers(CISCO_NAME)
        self.wait_for_adapter_down(CISCO_PLUGIN_NAME)
        self._toggle_parallel_fetch(False)

    def test_esx_parallel_fetch(self):
        self.settings_page.switch_to_page()
        self._toggle_parallel_fetch(True)

        self.adapters_page.switch_to_page()
        with EsxService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(ESX_NAME)
            self.adapters_page.click_adapter(ESX_NAME)
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_table_to_be_responsive()
            self.adapters_page.click_new_server()
            self.adapters_page.fill_creds(**esx_client_details[0][0])
            self.adapters_page.click_save_and_fetch()
            self.adapters_page.wait_for_spinner_to_end()

            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            assert self.devices_page.get_table_count() > 0
            self.adapters_page.clean_adapter_servers(ESX_NAME)
        self.wait_for_adapter_down(ESX_PLUGIN_NAME)
        self._toggle_parallel_fetch(False)
