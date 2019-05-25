import io

from test_helpers.machines import PROXY_PORT, PROXY_IP
from ui_tests.tests.instances_test_base import TestInstancesBase


class TestInstancesUpgrade(TestInstancesBase):

    def test_instances_upgrade(self):
        self.put_customer_conf_file()

        self.join_node()

        # upgrade
        self.check_upgrade()

    def check_upgrade(self):
        self.logger.info('Starting an upgrade')
        self.run_upgrade_on_node()
        self.logger.info('Upgrade finished')
        self._delete_nexpose_adapter_and_data()
        self._add_nexpose_adadpter_and_discover_devices()

    def run_upgrade_on_node(self):
        instance = self._instances[0]
        upgrade_script_path = '/home/ubuntu/upgrade.sh'
        upgrader = io.StringIO('#!/bin/bash\n'
                               'set -e\n'
                               'cd /home/ubuntu/\n'
                               f'export https_proxy=https://{PROXY_IP}:{PROXY_PORT}\n'  # bypass internet disconnect!
                               'wget https://s3.us-east-2.amazonaws.com/axonius-releases/latest/axonius_latest.py\n'
                               f'echo {instance.ssh_pass} | sudo -S python3 axonius_latest.py\n')

        instance.put_file(file_object=upgrader,
                          remote_file_path=upgrade_script_path)

        rc, out = instance.ssh(f'bash {upgrade_script_path}')
        if rc != 0:
            self.logger.info(f'ERROR: FAILED TO UPGRADE {out}')
        assert rc == 0
