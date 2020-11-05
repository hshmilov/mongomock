import io

import pytest

from axonius.consts.plugin_consts import MASTER_PROXY_PLUGIN_NAME
from scripts.automate_dev.download_version import get_export
from services.ports import DOCKER_PORTS
from ui_tests.tests.instances_test_base import TestInstancesBase


class TestInstancesUpgrade(TestInstancesBase):
    def test_instances_upgrade(self):
        self.setup_conf_files()

        self.join_node()

        # upgrade
        self.check_upgrade()
        self.check_ssh_tunnel()

    def check_upgrade(self):
        self.logger.info('Starting an upgrade')
        self.run_upgrade_on_node()
        self.logger.info('Upgrade finished')
        self.adapters_page.restore_json_client()
        self._add_adapter_and_discover_devices()

    def run_upgrade_on_node(self):
        instance = self._instances[0]
        upgrade_script_path = '/home/ubuntu/upgrade.sh'
        upgrade_file_name = 'axonius_latest.py'

        export = get_export(pytest.config.option.export_name)

        self.logger.info(f'Upgrading to version: {export["version"]}')

        # We added sleep of 10 minutes before we start downloading the upgrade file
        # the sleep is because on the first 5 minutes after connecting a node to its master it transfer a lot of
        # data back and forth and during this time the tinyproxy in master-proxy is under a lot of stress and sometime
        # it breaks and send illegal TLS that cause the connection to break.
        # These breaks can interrupt and even kill the updater image download process and as a result of that fail
        # the upgrade test.
        upgrader = io.StringIO('#!/bin/bash\n'
                               'set -e\n'
                               'cd /home/ubuntu/\n'
                               # bypass internet disconnect using our own node-proxy!
                               f'sleep 600\n'
                               f'curl --retry 15 -x https://localhost:{DOCKER_PORTS[MASTER_PROXY_PLUGIN_NAME]} '
                               f'-o {upgrade_file_name} {export["installer_download_link"]}\n'
                               f'echo {instance.ssh_pass} | sudo -S /bin/sh {upgrade_file_name}\n')

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
