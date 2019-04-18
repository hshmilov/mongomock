import re
import subprocess

import paramiko
import pytest

from test_credentials.test_ad_credentials import ad_client1_details
from test_credentials.test_nexpose_credentials import client_details
from ui_tests.tests.instances_test_base import TestInstancesBase

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
        read_until(chan, b'Please enter connection string:')
        chan.sendall(f'{master_ip_address} {node_join_token} node_1\n')
        try:
            read_until(chan, b'Node successfully joined Axonius cluster.\n')
        except Exception:
            self.logger.exception('Failed to connect node.')

    def check_password_change(self):
        with pytest.raises(paramiko.ssh_exception.AuthenticationException):
            self.connect_node_maker(self._instances[0])

        # Note that the usage of "{}" instead of NODE_NAME is due to a bug that is
        # caused because of the restart_system_on_boot because the master is derived
        # by test and not by export it is not subjected to a restart and the adapters_unique_name of it stay "_0".
        node_maker_password = self.instances_page.get_node_password('{}')
        self.connect_node_maker(self._instances[0], node_maker_password)

    def check_add_adapter_to_node(self):
        client_details.pop('verify_ssl')
        self.adapters_page.add_server(client_details, adapter_name=NEXPOSE_ADAPTER_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.run_filter_query(NEXPOSE_ADAPTER_FILTER)
        assert self.devices_page.count_entities() > 1
