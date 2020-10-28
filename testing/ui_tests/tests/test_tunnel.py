import time

import pytest

from axonius.consts.metric_consts import TunnelMetrics
from axonius.consts.plugin_consts import CORE_UNIQUE_NAME, AUDIT_COLLECTION
from axonius.saas.input_params import read_saas_input_params
from axonius.utils.wait import wait_until
from services.axon_service import TimeoutException
from test_credentials.test_ad_credentials import ad_client1_details
from test_helpers.log_tester import LogTester
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME, GUI_LOG_PATH

EMAIL_LIST_ID = 'emailList'
SUCCESS_TUNNEL_TOASTER = 'Tunnel settings saved successfully'
TEST_EMAIL = 'Im@Here.com'


class TestTunnel(TestBase):
    @pytest.mark.skipif(not read_saas_input_params(), reason='Can run only on a tunnel image')
    def test_tunnel_connected(self):
        self._verify_tunnel_status('Connected')
        log = self.axonius_system.db.get_collection(CORE_UNIQUE_NAME, AUDIT_COLLECTION).find_one({'category': 'tunnel'})
        assert log.get('action', None) == 'connected'

    @pytest.mark.skipif(not read_saas_input_params(), reason='Can run only on a tunnel image')
    def test_tunnel_disconnected(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_tunnel_settings()
        self._add_email_recipient(TEST_EMAIL)
        self.settings_page.save_and_wait_for_toaster(toaster_message=SUCCESS_TUNNEL_TOASTER)

        self.dashboard_page.switch_to_page()
        self.stop_tunnel(True)

        # Make sure notification was sent
        self.notification_page.wait_for_count(1)
        tester = LogTester(GUI_LOG_PATH)
        wait_until(lambda: tester.is_metric_in_log(TunnelMetrics.TUNNEL_DISCONNECTED, r'\d+'))
        assert tester.is_str_in_log(TEST_EMAIL)

        # Cleanup
        self.start_tunnel()

    @pytest.mark.skipif(not read_saas_input_params(), reason='Can run only on a tunnel image')
    def test_connect_adapter_to_tunnel(self):
        self._go_to_active_directory_adapter()
        self.adapters_page.click_advanced_settings()
        self._toggle_use_tunnel()
        time.sleep(90)

        self.adapters_page.safe_refresh()
        self.adapters_page.add_server(ad_client1_details)

        self.adapters_page.wait_for_server_green()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        assert self.devices_page.get_table_count() > 0
        self.users_page.switch_to_page()
        assert self.users_page.get_table_count() > 0
        self.adapters_page.clean_adapter_servers(AD_ADAPTER_NAME)

    @pytest.mark.skipif(not read_saas_input_params(), reason='Can run only on a tunnel image')
    def test_skip_adapter_fetch_if_tunnel_disconnected(self):
        # Initialize AD Adapter
        self.adapters_page.switch_to_page()
        self.adapters_page.search('microsoft')
        time.sleep(1)
        self.adapters_page.click_adapter(AD_ADAPTER_NAME)
        self.adapters_page.add_server(ad_client1_details)
        self.adapters_page.wait_for_server_green()

        # Make tunnel look disconnected
        try:
            self.axonius_system.openvpn.take_process_ownership()
            self.axonius_system.openvpn.stop()

            self.base_page.run_discovery()
            assert self.axonius_system.db.get_collection(CORE_UNIQUE_NAME, AUDIT_COLLECTION).find_one(
                {'action': 'skip'})
        # pylint: disable=try-except-raise
        except Exception:
            raise
        finally:
            # Cleanup
            self.wait_and_close_tunnel_modal()
            self.start_tunnel()

    @pytest.mark.skipif(not read_saas_input_params(), reason='Can run only on a tunnel image')
    def test_adapter_page_tunnel_user_notifications(self):
        self.settings_page.switch_to_page()
        self._verify_tunnel_status('Connected')
        self.dashboard_page.switch_to_page()

        self.stop_tunnel()
        self.wait_and_close_tunnel_modal()
        # check for tunnel status = disconnected and use_tunnel checkbox is enabled, message
        self._go_to_active_directory_adapter()
        self._test_click_button('Tunnel Settings')
        # goes back if click succeeded, if not an exception will trigger
        self._go_to_active_directory_adapter()

        self.adapters_page.click_advanced_settings()
        self._toggle_use_tunnel(False)
        self._test_click_button('Tunnel Installation Instructions')

        # cleanup
        self.start_tunnel()

    def _add_email_recipient(self, email):
        element = self.settings_page.find_element_by_xpath(
            f'//div[@id=\'{EMAIL_LIST_ID}\']//input[@type=\'text\']')
        self.settings_page.fill_text_by_element(element, email)
        self.settings_page.key_down_enter(element)

    def _go_to_active_directory_adapter(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.search('microsoft')
        time.sleep(1)
        self.adapters_page.click_adapter(AD_ADAPTER_NAME)

    def _toggle_use_tunnel(self, make_yes=True):
        self.adapters_page.click_advanced_configuration()
        self.adapters_page.click_toggle_button(
            self.adapters_page.find_checkbox_by_label('Use Tunnel to connect to source'),
            make_yes=make_yes)
        self.adapters_page.save_advanced_settings()
        try:
            self.adapters_page.wait_for_toaster('Adapter configuration saving in progress...')

            self.adapters_page.wait_for_toaster('Adapter configuration saved')
            self.adapters_page.wait_for_toaster_to_end('Adapter configuration saved')
        except Exception:
            # Sometimes its too fast
            pass

    def _verify_tunnel_status(self, status, refresh=False):
        if refresh:
            self.settings_page.hard_refresh()
        self.settings_page.switch_to_page()
        self.settings_page.click_tunnel_settings()
        button = self.settings_page.wait_for_element_present_by_css('.tunnel-status-btn')
        self.settings_page.wait_for_element_present_by_text('Loading...', button)
        self.settings_page.wait_for_element_absent_by_text('Loading...', button)
        assert self.settings_page.wait_for_element_present_by_text(status, button, retries=10)

    def _test_click_button(self, text):
        return self.adapters_page.get_button(text).click()

    def wait_and_close_tunnel_modal(self):
        self.settings_page.wait_for_tunnel_disconnected_modal()
        self.settings_page.close_tunnel_disconnected_modal()

    def stop_tunnel(self, wait_before=False):
        self.axonius_system.openvpn.take_process_ownership()
        self.axonius_system.openvpn.stop()
        time.sleep(5)
        if wait_before:
            self.wait_and_close_tunnel_modal()
        self._verify_tunnel_status('Disconnected')

    def start_tunnel(self):
        self.axonius_system.openvpn.take_process_ownership()
        self.axonius_system.openvpn.start()
        time.sleep(15)
        wait_until(lambda: self._verify_tunnel_status('Connected', True), check_return_value=False,
                   tolerated_exceptions_list=[TimeoutException], total_timeout=240, interval=0)
        time.sleep(15)
