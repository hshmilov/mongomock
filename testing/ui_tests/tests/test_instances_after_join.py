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
    NEXPOSE_ADAPTER_NAME, wait_for_booted_for_production, UPDATE_HOSTNAME


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
        self.update_hostname_form_gui_and_check_slave_node()
        self.check_deactivate_node()
        self.check_ssh_tunnel()
        self.check_node_restart()
        self.check_master_disconnect()

    def check_add_adapter_to_node(self):
        self._add_nexpose_adadpter_and_discover_devices()

    def check_node_restart(self):
        self._delete_nexpose_adapter_and_data()

        # Using bare sshc.exec_command because we want to fire and forget.
        # Sync files
        self._instances[0].sshc.exec_command('sudo sh -c "echo s > /proc/sysrq-trigger"')
        # Do a hard reboot
        self._instances[0].sshc.exec_command('sudo sh -c "echo b > /proc/sysrq-trigger"')

        time.sleep(5)
        self._instances[0].wait_for_ssh()
        wait_for_booted_for_production(self._instances[0])
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

    def get_hostname_from_node(self):
        rc, output = self._instances[0].ssh('cat /etc/hostname')
        self.logger.debug(f'/etc/hostname return rc is {rc}')
        self.logger.debug(f'/etc/hostname return output is {output}')
        self._instances[0].sshc.close()
        self._instances[0].wait_for_ssh()
        return output

    def check_correct_hostname_is_shown_in_table(self):
        node_hostname_from_table = self.instances_page.get_node_hostname(NODE_NAME)
        self.logger.info(f'{NODE_NAME} hostname recognised as:{node_hostname_from_table}')
        assert node_hostname_from_table == NODE_HOSTNAME, 'System did not recognize node hostname correctly.'

    def check_change_node_name(self):
        def _test_dropdown_change():
            self.adapters_page.switch_to_page()
            self.adapters_page.refresh()
            self.adapters_page.wait_for_adapter(NEXPOSE_ADAPTER_NAME)
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

    def _check_nexpose_in_list(self, should_be_in_list=True):
        # Check that adapters from that node don't appear in adapters table.
        self.adapters_page.switch_to_page()
        self.adapters_page.refresh()
        self.adapters_page.wait_for_spinner_to_end()
        adapters_list = self.adapters_page.get_adapter_list()
        assert should_be_in_list == any(['nexpose' in adapter[0].lower() for adapter in adapters_list])

    def check_deactivate_node(self):
        # Deactivate node.
        self.instances_page.switch_to_page()
        self.instances_page.find_query_row_by_name(NEW_NODE_NAME).find_elements_by_class_name('x-checkbox')[0].click()
        self.instances_page.deactivate_instances()

        # Check that it's status changed.
        assert self.instances_page.get_node_status_by_name(NEW_NODE_NAME) == 'Deactivated'

        wait_until(lambda: self._check_nexpose_in_list(False), interval=2.0, check_return_value=False,
                   tolerated_exceptions_list=[AssertionError])

        # Reactivate node
        self.instances_page.switch_to_page()
        self.instances_page.find_query_row_by_name(NEW_NODE_NAME).find_elements_by_class_name('x-checkbox')[0].click()
        self.instances_page.reactivate_instances()

        # Check that it's status changed.
        assert self.instances_page.get_node_status_by_name(NEW_NODE_NAME) == 'Activated'

        # Check that adapters from that node reappear in adapters table.
        wait_until(self._check_nexpose_in_list, interval=1.0, check_return_value=False,
                   tolerated_exceptions_list=[AssertionError])

        # Re-adding client after deactivation deleted it (without it's devices).
        self._add_nexpose_adadpter_and_discover_devices()

    def verify_hostname_changed(self):
        output = self.get_hostname_from_node()
        if output == UPDATE_HOSTNAME:
            return True
        self.logger.debug(f'verification: /etc/hostname ser to current:{output}  expected:{NODE_HOSTNAME}')
        return False

    def update_hostname_form_gui_and_check_slave_node(self):

        self.logger.info('SUB TEST  1 : Negative Flow hostname with space should fail validation ')
        self.instances_page.switch_to_page()
        illegal_hostname = 'BAD HOSTNAME'
        self.instances_page.change_instance_hostname(current_node_name=NEW_NODE_NAME,
                                                     new_hostname=illegal_hostname,
                                                     negative_test=True)
        self.logger.info('SUB TEST  2 : Positive Flow update hostname')
        self.instances_page.switch_to_page()

        self.instances_page.change_instance_hostname(current_node_name=NEW_NODE_NAME,
                                                     new_hostname=UPDATE_HOSTNAME)

        wait_until(self.verify_hostname_changed,
                   total_timeout=3,
                   interval=3)

        # at this point test pass,  reverting hostname to original.
        self.instances_page.change_instance_hostname(current_node_name=NEW_NODE_NAME,
                                                     new_hostname=NODE_HOSTNAME)
