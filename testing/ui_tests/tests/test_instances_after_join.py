import subprocess
import time

import paramiko
from retry.api import retry_call
from selenium.common.exceptions import NoSuchElementException

from axonius.utils.wait import wait_until, expect_specific_exception_to_be_raised
from services.adapters.ad_service import AdService
from services.adapters.json_file_service import JsonFileService
from test_credentials.test_ad_credentials import ad_client1_details
from ui_tests.tests.instances_test_base import TestInstancesBase, NODE_NAME, NODE_HOSTNAME, NEW_NODE_NAME, \
    NEXPOSE_ADAPTER_NAME


class TestInstancesAfterNodeJoin(TestInstancesBase):

    def test_instances_after_join(self):
        self.put_customer_conf_file()

        # Adding adapter and data for later usage.
        self.adapters_page.add_server(ad_client1_details)
        self.adapters_page.wait_for_spinner_to_end()
        self.base_page.run_discovery()
        self.change_node_hostname()

        self.join_node()

        self.check_password_change()
        self.check_add_adapter_to_node()
        self.check_correct_ip_is_shown_in_table()
        self.check_correct_hostname_is_shown_in_table()
        self.check_change_node_name()
        self.check_ssh_tunnel()
        self.check_node_restart()
        self.check_master_disconnect()

    def check_add_adapter_to_node(self):
        self._add_nexpose_adadpter_and_discover_devices()

    def check_node_restart(self):
        self._delete_nexpose_adapter_and_data()
        self._instances[0].ssh('echo \'{self._instances[0].ssh_pass}\' | sudo -S reboot')
        time.sleep(5)
        self._instances[0].wait_for_ssh()
        self._add_nexpose_adadpter_and_discover_devices()

    def _try_discovery_until_check_devices_count_goes_up(self):
        self.base_page.run_discovery()
        return self._check_device_count() > 1

    def check_master_disconnect(self):
        local_json_adapter = JsonFileService()
        local_json_adapter.take_process_ownership()
        local_ad_adapter = AdService()
        local_ad_adapter.take_process_ownership()

        self.adapters_page.remove_server(delete_associated_entities=True)
        time.sleep(5)
        self.devices_page.delete_devices()

        self.axonius_system.take_process_ownership()
        self.axonius_system.stop()

        subprocess.check_call('weave stop'.split())
        self.axonius_system.start_and_wait()
        self.login_page.wait_for_login_page_to_load()
        self.login()

        wait_until(self._try_discovery_until_check_devices_count_goes_up, total_timeout=60 * 3, interval=30,
                   tolerated_exceptions_list=[NoSuchElementException])

    def check_password_change(self):
        # Wait for node to change node_maker password after connection.
        wait_until(lambda: self.instances_page.get_node_password(NODE_NAME) != '',
                   tolerated_exceptions_list=[NoSuchElementException])
        try:
            self.logger.info(
                f'{NODE_NAME} node_maker password changed to:{self.instances_page.get_node_password(NODE_NAME)}')

            # Since we're waiting for the password to change and the ssh login with the old one to raise an exception.
            self.logger.info('Trying to connect to node_maker with old password')
            wait_until(
                lambda: expect_specific_exception_to_be_raised(lambda: self.connect_node_maker(self._instances[0]),
                                                               paramiko.ssh_exception.AuthenticationException),
                total_timeout=60 * 5,
                error_message='No exception was raised while trying connect to node with old password.')
        except Exception:
            self.logger.exception(
                'Failed to connect to node with old password as expected but a bad exception was raised.')
            raise

        # Note that the usage of "{}" instead of NODE_NAME is due to a bug that is
        # caused because of the restart_system_on_boot because the master is derived
        # by test and not by export it is not subjected to a restart and the adapters_unique_name of it stay "_0".
        node_maker_password = self.instances_page.get_node_password(NODE_NAME)
        self.logger.info(f'Trying password len({len(node_maker_password)}): "{node_maker_password[:4]}..."')
        retry_call(lambda: self.connect_node_maker(self._instances[0], node_maker_password), tries=5, delay=10)

    def check_correct_ip_is_shown_in_table(self):
        node_ip_from_table = self.instances_page.get_node_ip(NODE_NAME)
        self.logger.info(f'{NODE_NAME} IP recognised as:{node_ip_from_table}')
        assert node_ip_from_table == self._instances[0].ip, 'System did not recognize node IP correctly.'

    def change_node_hostname(self):
        self._instances[0].ssh(f'echo \'{self._instances[0].ssh_pass}\' | sudo -S hostname {NODE_HOSTNAME}')
        self._instances[0].ssh(f'echo \'{NODE_HOSTNAME}\' > /tmp/temp_name_file')
        self._instances[0].ssh(f'echo \'{self._instances[0].ssh_pass}\' | sudo -S mv /tmp/temp_name_file /etc/hostname')
        self._instances[0].sshc.close()
        self._instances[0].wait_for_ssh()

    def check_correct_hostname_is_shown_in_table(self):
        node_hostname_from_table = self.instances_page.get_node_hostname(NODE_NAME)
        self.logger.info(f'{NODE_NAME} hostname recognised as:{node_hostname_from_table}')
        assert node_hostname_from_table == NODE_HOSTNAME, 'System did not recognize node hostname correctly.'

    def check_change_node_name(self):
        def _test_dropdown_change():
            self.adapters_page.switch_to_page()
            self.adapters_page.refresh()
            self.adapters_page.click_adapter(NEXPOSE_ADAPTER_NAME)
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.click_new_server()
            select_value = self.adapters_page.get_instances_dropdown_selected_value()
            self.adapters_page.click_cancel()
            assert select_value == NEW_NODE_NAME, \
                'Node name was not changed in the adapters instances select dropdown.'
        self.instances_page.change_instance_name(NODE_NAME, NEW_NODE_NAME)
        node_hostname_from_table = self.instances_page.get_node_hostname(NEW_NODE_NAME)
        assert node_hostname_from_table == NODE_HOSTNAME, 'System did not recognize node hostname correctly.'
        wait_until(_test_dropdown_change, check_return_value=False, tolerated_exceptions_list=[AssertionError])
