import subprocess
import time

import paramiko
from selenium.common.exceptions import NoSuchElementException

from axonius.utils.wait import wait_until, expect_specific_exception_to_be_raised
from services.adapters.ad_service import AdService
from services.adapters.json_file_service import JsonFileService
from test_credentials.test_ad_credentials import ad_client1_details
from ui_tests.tests.instances_test_base import TestInstancesBase, NODE_NAME, NODE_HOSTNAME


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

    def check_master_disconnect(self):
        local_json_adapter = JsonFileService()
        local_json_adapter.take_process_ownership()
        local_ad_adapter = AdService()
        local_ad_adapter.take_process_ownership()
        try:
            local_json_adapter.stop()
            local_ad_adapter.stop()

            self.adapters_page.remove_server(delete_associated_entities=True)
            time.sleep(5)
            self.devices_page.delete_devices()

            self.axonius_system.take_process_ownership()
            self.axonius_system.stop()

            subprocess.check_call('weave stop'.split())
            self.axonius_system.start_and_wait()
            self.login_page.wait_for_login_page_to_load()
            self.login()
            self.devices_page.switch_to_page()
            self.base_page.run_discovery()
            wait_until(lambda: self._check_device_count() > 1, total_timeout=90, interval=20)
        finally:
            local_ad_adapter.start_and_wait()
            local_json_adapter.start_and_wait()

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
        self.connect_node_maker(self._instances[0], node_maker_password)

    def change_node_hostname(self):
        self._instances[0].ssh(f'echo \'{self._instances[0].ssh_pass}\' | sudo -S hostname {NODE_HOSTNAME}')
        self._instances[0].ssh(
            f'echo \'{self._instances[0].ssh_pass}\' | sudo -S echo "{NODE_HOSTNAME}" > /etc/hostname')
        self._instances[0].sshc.close()
        self._instances[0].wait_for_ssh()
