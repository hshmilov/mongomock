import time

from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException

from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AWS_ADAPTER_NAME, AWS_ADAPTER, SHODAN_ADAPTER
from services.adapters.aws_service import AwsService
from services.adapters.shodan_service import ShodanService
from test_credentials.test_aws_credentials import client_details as aws_client_details
from axonius.utils.wait import wait_until


ENFORCEMENT_NAME = 'lalala'
SHODAN_ACTION_NAME = 'my shodan'

ASSET_NAME = 'diag-proxy'
QUERY = f'(specific_data.data.name == "{ASSET_NAME}")'


class TestEnforcementActions(TestBase):
    def _does_shodan_exist(self):
        self.devices_page.safe_refresh()
        self.devices_page.find_element_by_text('Shodan').click()
        self.devices_page.find_element_by_text('Shodan Data')

    def test_shodan(self):
        self.settings_page.switch_to_page()

        with AwsService().contextmanager(take_ownership=True), ShodanService().contextmanager(take_ownership=True):
            self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[0][0])
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_server_green()
            self.adapters_page.wait_for_data_collection_toaster_absent()

            self.base_page.run_discovery()

            # restart gui service for master instance to be available at node selection.
            # should be deleted when AX-4451 is done
            gui_service = self.axonius_system.gui
            gui_service.take_process_ownership()
            gui_service.stop(should_delete=False)
            gui_service.start_and_wait()
            time.sleep(5)
            self.login()
            self.settings_page.switch_to_page()
            self.base_page.run_discovery()

            self.enforcements_page.create_basic_enforcement(ENFORCEMENT_NAME, trigger=False)
            self.enforcements_page.add_main_action_shodan(SHODAN_ACTION_NAME)

            self.devices_page.switch_to_page()
            self.devices_page.enforce_action_on_query(QUERY, ENFORCEMENT_NAME)

            self.devices_page.click_row_checkbox()
            self.devices_page.click_row()

            wait_until(self._does_shodan_exist,
                       check_return_value=False,
                       total_timeout=5 * 60,
                       tolerated_exceptions_list=[NoSuchElementException, ElementNotInteractableException])

            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)
        self.wait_for_adapter_down(SHODAN_ADAPTER)
        self.wait_for_adapter_down(AWS_ADAPTER)
