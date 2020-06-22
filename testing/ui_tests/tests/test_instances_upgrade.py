import io

import pytest

from axonius.consts.plugin_consts import MASTER_PROXY_PLUGIN_NAME
from scripts.automate_dev.download_version import get_export
from services.ports import DOCKER_PORTS
from ui_tests.tests.instances_test_base import TestInstancesBase


class TestInstancesUpgrade(TestInstancesBase):

    @pytest.mark.skip('Might get all tests after stuck.')
    def test_instances_upgrade(self):
        self.put_customer_conf_file()

        self.join_node()

        # upgrade
        self.check_upgrade()
        self.check_ssh_tunnel()

    def check_upgrade(self):
        self.logger.info('Starting an upgrade')
        self.run_upgrade_on_node()
        self.logger.info('Upgrade finished')
        self._delete_nexpose_adapter_and_data()
        self._add_nexpose_adadpter_and_discover_devices()

    def run_upgrade_on_node(self):
        instance = self._instances[0]
        upgrade_script_path = '/home/ubuntu/upgrade.sh'
        upgrade_file_name = 'axonius_latest.py'

        export = get_export(pytest.config.option.export_name)

        self.logger.info(f'Upgrading to version: {export["version"]}')

        upgrader = io.StringIO('#!/bin/bash\n'
                               'set -e\n'
                               'cd /home/ubuntu/\n'
                               # bypass internet disconnect using our own node-proxy!
                               f'export https_proxy=https://localhost:{DOCKER_PORTS[MASTER_PROXY_PLUGIN_NAME]}\n'
                               f'wget -O {upgrade_file_name} {export["installer_download_link"]}\n'
                               f'echo {instance.ssh_pass} | sudo -S python3 axonius_latest.py\n')

        instance.put_file(file_object=upgrader,
                          remote_file_path=upgrade_script_path)

        rc, out = instance.ssh(f'bash {upgrade_script_path}')
        if rc != 0:
            self.logger.info(f'ERROR: FAILED TO UPGRADE {out}')
        assert rc == 0
        self.logger.info(f'upgrade output: {out}')
        port = DOCKER_PORTS[MASTER_PROXY_PLUGIN_NAME]
        rc, out = instance.ssh(f'export https_proxy=https://localhost:{port} && curl https://manage.chef.io')
        if rc != 0:
            self.logger.info(f'proxy failed: {out}')
        assert rc == 0
