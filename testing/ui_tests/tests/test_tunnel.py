import os
import time

import pytest

from axonius.consts.metric_consts import TunnelMetrics
from axonius.consts.plugin_consts import CORE_UNIQUE_NAME, AUDIT_COLLECTION
from axonius.saas.input_params import read_saas_input_params
from axonius.utils.wait import wait_until
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
        self.settings_page.switch_to_page()
        self.settings_page.click_tunnel_settings()
        self.settings_page.wait_for_element_absent_by_text('Checking...')
        assert self.settings_page.wait_for_element_present_by_text('Connected')
        log = self.axonius_system.db.get_collection(CORE_UNIQUE_NAME, AUDIT_COLLECTION).find_one({'category': 'tunnel'})
        assert log.get('action', None) == 'connected'

    @pytest.mark.skipif(not read_saas_input_params(), reason='Can run only on a tunnel image')
    def test_tunnel_disconnected(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_tunnel_settings()
        self._add_email_recipient(TEST_EMAIL)
        self.settings_page.save_and_wait_for_toaster(toaster_message=SUCCESS_TUNNEL_TOASTER)

        os.system('sudo iptables -I INPUT 1 -p tcp -m tcp --dport 2212 -j DROP')
        try:
            self.axonius_system.openvpn.take_process_ownership()
            self.axonius_system.openvpn.stop()
            self.axonius_system.openvpn.start()

            self.settings_page.switch_to_page()
            self.settings_page.click_tunnel_settings()
            self.settings_page.wait_for_element_absent_by_text('Checking...')
            assert self.settings_page.wait_for_element_present_by_text('Disconnected')
            # Make sure notification was sent
            self.notification_page.wait_for_count(1)
            tester = LogTester(GUI_LOG_PATH)
            wait_until(lambda: tester.is_metric_in_log(TunnelMetrics.TUNNEL_DISCONNECTED, r'\d+'))
            assert tester.is_str_in_log(TEST_EMAIL)
        # pylint: disable=try-except-raise
        except Exception:
            raise
        finally:
            # Cleanup
            os.system('sudo iptables -D INPUT -p tcp -m tcp --dport 2212 -j DROP')
            self.axonius_system.openvpn.take_process_ownership()
            self.axonius_system.openvpn.stop()
            time.sleep(5)
            self.axonius_system.openvpn.start()

    @pytest.mark.skipif(not read_saas_input_params(), reason='Can run only on a tunnel image')
    def test_connect_adapter_to_tunnel(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.search('microsoft')
        time.sleep(1)
        self.adapters_page.click_adapter(AD_ADAPTER_NAME)
        self.adapters_page.click_advanced_settings()
        self.adapters_page.click_advanced_configuration()
        self.adapters_page.click_toggle_button(
            self.adapters_page.find_checkbox_by_label('Use Tunnel to connect to source'),
            make_yes=True)
        self.adapters_page.save_advanced_settings()
        try:
            self.adapters_page.wait_for_toaster('Adapter configuration saving in progress...')

            self.adapters_page.wait_for_toaster('Adapter configuration saved')
            self.adapters_page.wait_for_toaster_to_end('Adapter configuration saved')
        except Exception:
            # Sometimes its too fast
            pass
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
            self.axonius_system.openvpn.start()

    def _add_email_recipient(self, email):
        element = self.settings_page.find_element_by_xpath('//div[@id=\'emailList\']//input[@type=\'text\']')
        self.settings_page.fill_text_by_element(element, email)
        self.settings_page.key_down_enter(element)
