import os
import subprocess
import time

import pytest

from axonius.consts.plugin_consts import CORE_UNIQUE_NAME, AUDIT_COLLECTION
from axonius.saas.input_params import read_saas_input_params
from test_credentials.test_ad_credentials import ad_client1_details
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME


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
        # pylint: disable=try-except-raise
        except Exception:
            raise
        finally:
            # Cleanup
            os.system('sudo iptables -D INPUT -p tcp -m tcp --dport 2212 -j DROP')

    @pytest.mark.skipif(not read_saas_input_params(), reason='Can run only on a tunnel image')
    def test_connect_adapter_to_tunnel(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.search('microsoft')
        self.adapters_page.click_adapter(AD_ADAPTER_NAME)
        self.adapters_page.click_advanced_settings()
        self.adapters_page.click_advanced_configuration()
        self.adapters_page.click_toggle_button(
            self.adapters_page.find_checkbox_by_label('Use Tunnel to connect to source'),
            make_yes=True)
        self.adapters_page.save_advanced_settings()
        self.adapters_page.wait_for_toaster('Adapter configuration saving in progress...')
        try:
            self.adapters_page.wait_for_toaster('Adapter configuration saved')
            self.adapters_page.wait_for_toaster_to_end('Adapter configuration saved')
        except Exception:
            # Adapter uwsgi probably taking time to load
            nics = ''
            tries = 0
            while 'eth2' not in nics and tries < 5:
                tries += 1
                time.sleep(60)
                try:
                    nics = subprocess.check_output(
                        'sudo docker exec -it active-directory-adapter ifconfig -a'.split(' ')).decode('utf-8')
                except subprocess.SubprocessError:
                    continue

        self.adapters_page.click_advanced_configuration()
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
