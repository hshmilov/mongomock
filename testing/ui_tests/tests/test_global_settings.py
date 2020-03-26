import pytest

from retrying import retry
from selenium.common.exceptions import NoSuchElementException

from axonius.utils.wait import wait_until
from scripts.instances.instances_consts import PROXY_DATA_HOST_PATH
from services.plugins.gui_service import GuiService
from services.standalone_services.smtp_service import SmtpService
from test_helpers.log_tester import LogTester
from test_helpers.machines import PROXY_IP, PROXY_PORT
from ui_tests.tests.ui_consts import GUI_LOG_PATH
from ui_tests.tests.ui_test_base import TestBase

from testing.test_credentials.test_ad_credentials import ad_client1_details

INVALID_EMAIL_HOST = 'dada...$#@'


class TestGlobalSettings(TestBase):
    def test_email_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)

        # Invalid host is not being tested, an open bug
        # self.settings_page.fill_email_host(INVALID_EMAIL_HOST)

        self.settings_page.fill_email_port(-5)
        assert self.settings_page.get_email_port() == '5'

        # Ports above the maximum are also not validated
        # self.settings_page.fill_email_port(555)
        # self.settings_page.fill_email_port(88888)
        # self.settings_page.find_email_port_error()

    def test_email_host_validation(self):
        smtp_service = SmtpService()
        smtp_service.take_process_ownership()

        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)

        self.settings_page.fill_email_host(smtp_service.fqdn)
        self.settings_page.fill_email_port(smtp_service.port)

        self.settings_page.click_save_global_settings()
        self.settings_page.wait_email_connection_failure_toaster(smtp_service.fqdn)

        with smtp_service.contextmanager():
            self.settings_page.click_save_button()
            self.settings_page.wait_for_saved_successfully_toaster()

        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False, scroll_to_toggle=False)
        self.settings_page.click_save_global_settings()

    def test_maintenance_endpoints(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.toggle_advanced_settings()
        gui_service = GuiService()

        assert gui_service.troubleshooting().strip() == b'true'
        toggle = self.settings_page.find_remote_support_toggle()
        assert self.settings_page.is_toggle_selected(toggle)

        self.settings_page.set_remote_support_toggle(make_yes=False)
        wait_until(lambda: gui_service.troubleshooting().strip() == b'false')

        self.settings_page.set_remote_support_toggle(make_yes=True)
        wait_until(lambda: gui_service.troubleshooting().strip() == b'true')

        assert gui_service.analytics().strip() == b'true'
        toggle = self.settings_page.find_analytics_toggle()
        assert self.settings_page.is_toggle_selected(toggle)

        self.settings_page.set_analytics_toggle(make_yes=False)
        wait_until(lambda: gui_service.analytics().strip() == b'false')

        self.settings_page.set_analytics_toggle(make_yes=True)
        wait_until(lambda: gui_service.analytics().strip() == b'true')

    def test_remote_access_log(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.toggle_advanced_settings()

        self.settings_page.set_provision_toggle(make_yes=False)
        self.settings_page.fill_remote_access_timeout('0.01')  # 36 seconds
        self.settings_page.click_start_remote_access()
        wait_until(
            lambda: LogTester(GUI_LOG_PATH).is_pattern_in_log(
                '(Creating a job for stopping the maintenance|Job already existing - updating its run time to)', 10))
        assert self.axonius_system.gui.provision().strip() == b'true'
        wait_until(lambda: self.axonius_system.gui.provision().strip() == b'false', total_timeout=60 * 1.5)

    def test_proxy_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.wait_for_spinner_to_end()

        self.settings_page.set_proxy_settings_enabled()
        self.settings_page.fill_proxy_address(PROXY_IP)
        port = str(PROXY_PORT)
        self.settings_page.fill_proxy_port(port)
        self.settings_page.save_and_wait_for_toaster()

        @retry(wait_fixed=1000, stop_max_attempt_number=60 * 2)
        def proxy_settings_propagate():
            content = PROXY_DATA_HOST_PATH.read_text().strip()
            assert content == f'{{"creds": "{PROXY_IP}:{port}", "verify": true}}'

        proxy_settings_propagate()

    def test_bad_proxy_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.wait_for_spinner_to_end()

        self.settings_page.set_proxy_settings_enabled()
        self.settings_page.fill_proxy_address('1.2.3.4')
        self.settings_page.fill_proxy_port('1234')
        self.settings_page.click_save_global_settings()
        self.settings_page.wait_for_toaster(self.settings_page.BAD_PROXY_TOASTER)

    def test_require_connection_label_setting(self):
        # save without connection label
        assert not self.settings_page.get_connection_label_required_value()
        self.adapters_page.add_server(ad_client1_details)
        self.adapters_page.wait_for_data_collection_toaster_start()
        self.adapters_page.remove_server(ad_client1_details)

        # make connection label required
        self.settings_page.toggle_connection_label_required()
        self.settings_page.click_save_button()
        self.settings_page.wait_for_saved_successfully_toaster()
        assert self.settings_page.get_connection_label_required_value()

        # verify that save fails without connection label
        with pytest.raises(NoSuchElementException):
            self.adapters_page.add_server(ad_client1_details)
        self.adapters_page.click_cancel()

        # verify that save succeeds with connection label
        ad_client1_details['connectionLabel'] = 'connection'
        self.adapters_page.add_server(ad_client1_details)
        self.adapters_page.wait_for_data_collection_toaster_start()

        # clean up
        self.adapters_page.remove_server(ad_client1_details)
        self.settings_page.toggle_connection_label_required()
        self.settings_page.click_save_button()
        self.settings_page.wait_for_saved_successfully_toaster()
        assert not self.settings_page.get_connection_label_required_value()
