from axonius.consts.system_consts import LOGS_PATH_HOST
from axonius.utils.wait import wait_until
from services.plugins.bandicoot_service import BandicootService
from services.plugins.postgres_service import PostgresService

from test_credentials.test_gui_credentials import AXONIUS_USER
from test_helpers.log_tester import LogTester
from ui_tests.tests.ui_test_base import TestBase

TRANSFER_BANDICOOT = 'Starting transfer'


class TestAutomaticBandicoot(TestBase):

    def test_automatic_bandicoot(self):
        self.devices_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        toggle = self.settings_page.find_activate_bandicoot_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=True)
        self.settings_page.click_save_button()
        self.settings_page.wait_for_saved_successfully_toaster()

        PostgresService().wait_for_service(timeout=900)
        BandicootService().wait_for_service(timeout=900)

        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        bandicoot_file = LogTester(f'{LOGS_PATH_HOST}/bandicoot/bandicoot.axonius.log')
        wait_until(lambda: bandicoot_file.is_str_in_log(
            TRANSFER_BANDICOOT, 1000), tolerated_exceptions_list=[Exception])

        self.login_page.logout()

        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        toggle = self.settings_page.find_activate_bandicoot_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False, scroll_to_toggle=True)
        self.settings_page.click_save_button()
        self.settings_page.wait_for_saved_successfully_toaster()

        wait_until(lambda: not BandicootService().get_is_container_up())
        wait_until(lambda: not PostgresService().get_is_container_up())
