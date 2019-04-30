import re
import subprocess
import time

import paramiko
import pytest

from axonius.utils.wait import wait_until
from test_credentials.test_ad_credentials import ad_client1_details
from test_credentials.test_nexpose_credentials import client_details
from ui_tests.tests.instances_test_base import TestInstancesBase
from services.adapters.ad_service import AdService
from services.adapters.json_file_service import JsonFileService

PRIVATE_IP_ADDRESS_REGEX = r'inet (10\..*|192\.168.*|172\..*)\/'

MAX_CHARS = 10 ** 6
TIMEOUT = 50
NODE_NAME = 'node_1'
NEXPOSE_ADAPTER_NAME = 'Rapid7 Nexpose'
NEXPOSE_ADAPTER_FILTER = 'adapters == "nexpose_adapter"'


class TestInstancesAfterNodeJoin(TestInstancesBase):

    def test_instances_after_join(self):
        # Adding adapter and data for later usage.
        self.adapters_page.add_server(ad_client1_details)
        self.adapters_page.wait_for_spinner_to_end()
        self.base_page.run_discovery()

        self.node_join()

        self.check_password_change()
        self.check_add_adapter_to_node()
        self.check_node_restart()
        self.check_master_disconnect()

    def node_join(self):
        def read_until(ssh_chan, what):
            data = b''
            for _ in range(MAX_CHARS):
                c = ssh_chan.recv(1024)
                if not c:
                    raise RuntimeError('Connection Closed')
                data += c
                if data.endswith(what):
                    break
            return data

        ip_output = subprocess.check_output(['ip', 'a']).decode('utf-8')
        master_ip_address = re.search(PRIVATE_IP_ADDRESS_REGEX, ip_output).group(1)
        node_join_token = self.instances_page.get_node_join_token()
        ssh_client = self.connect_node_maker(self._instances[0])
        chan = ssh_client.get_transport().open_session()
        chan.settimeout(TIMEOUT)
        chan.invoke_shell()
        node_join_message = read_until(chan, b'Please enter connection string:')
        self.logger.info(f'node_maker login message: {node_join_message.decode("utf-8")}')
        chan.sendall(f'{master_ip_address} {node_join_token} {NODE_NAME}\n')
        try:
            node_join_log = read_until(chan, b'Node successfully joined Axonius cluster.\n')
            self.logger.info(f'node join log: {node_join_log.decode("utf-8")}')
        except Exception:
            self.logger.exception('Failed to connect node.')

        self.instances_page.wait_until_node_appears_in_table(NODE_NAME)

    def check_password_change(self):
        with pytest.raises(paramiko.ssh_exception.AuthenticationException):
            self.connect_node_maker(self._instances[0])

        # Note that the usage of "{}" instead of NODE_NAME is due to a bug that is
        # caused because of the restart_system_on_boot because the master is derived
        # by test and not by export it is not subjected to a restart and the adapters_unique_name of it stay "_0".
        node_maker_password = self.instances_page.get_node_password(NODE_NAME)
        self.connect_node_maker(self._instances[0], node_maker_password)

    def _add_nexpose_adadpter_and_discover_devices(self):
        # Using nexpose on all these test since i do not raise
        # nexpose as part of the tests so the only nexpose adapter present
        # should be from the node (and the client add should only have that option)
        # and for any reason it is not present than we have an instances bug.
        client_details.pop('verify_ssl', None)
        self.adapters_page.add_server(client_details, adapter_name=NEXPOSE_ADAPTER_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.base_page.run_discovery()
        wait_until(lambda: self._check_device_count() > 1, total_timeout=90, interval=20)

    def _check_device_count(self):
        self.devices_page.switch_to_page()
        self.devices_page.refresh()
        self.devices_page.run_filter_query(NEXPOSE_ADAPTER_FILTER)
        return self.devices_page.count_entities()

    def _delete_nexpose_adapter_and_data(self):
        client_details.pop('verify_ssl', None)
        self.adapters_page.remove_server(adapter_name=NEXPOSE_ADAPTER_NAME, delete_associated_entities=True)
        wait_until(lambda: self._check_device_count() == 0, total_timeout=90, interval=20)

    def check_add_adapter_to_node(self):
        self._add_nexpose_adadpter_and_discover_devices()

    def check_node_restart(self):
        self._delete_nexpose_adapter_and_data()
        self._instances[0].ssh('sudo reboot')
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
