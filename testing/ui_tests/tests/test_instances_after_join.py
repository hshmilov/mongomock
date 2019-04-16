import re
import subprocess

from ui_tests.tests.instances_test_base import TestInstancesBase

PRIVATE_IP_ADDRESS_REGEX = r'inet (10\..*|192\.168.*|172\..*)\/'

MAX_CHARS = 10 ** 6
TIMEOUT = 50


class TestInstancesAfterNodeJoin(TestInstancesBase):

    def test_instances_after_join(self):
        self.node_join()

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
