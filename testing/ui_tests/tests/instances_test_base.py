import os
import sys
from pathlib import Path

import paramiko
import pytest
from retrying import retry

from builds import Builds
from builds.builds_factory import BuildsInstance
from devops.scripts.instances.start_system_on_first_boot import \
    BOOTED_FOR_PRODUCTION_MARKER_PATH
from ui_tests.tests.ui_test_base import TestBase

NODE_MAKER_USERNAME = 'node_maker'
NODE_MAKER_PASSWORD = 'M@ke1tRain'

DEFAULT_IMAGE_USERNAME = 'ubuntu'
DEFAULT_IMAGE_PASSWORD = 'bringorder'
AUTO_TEST_VM_KEY_PAIR = 'Auto-Test-VM-Key'

RESTART_LOG_PATH = Path('/var/log/start_system_on_reboot.log')

DEFAULT_LIMIT = 10


@retry(stop_max_attempt_number=90, wait_fixed=1000 * 20)
def wait_for_booted_for_production(instance: BuildsInstance):
    print('Waiting for server to be booted for production...')
    test_ready_command = f'ls -al {BOOTED_FOR_PRODUCTION_MARKER_PATH.absolute().as_posix()}'
    state = instance.ssh(test_ready_command)
    assert 'root root' in state[1]


def bring_restart_on_reboot_node_log(instance: BuildsInstance, logger):
    get_log_command = f'tail {RESTART_LOG_PATH.absolute().as_posix()}'
    restart_log_tail = instance.ssh(get_log_command)
    logger.info(f'/var/log/start_system_on_reboot.log : {restart_log_tail[1]}')


def setup_instances(logger, instance_name, export_name=None):
    builds_instance = Builds()
    if export_name:
        latest_export = builds_instance.get_export_by_name(export_name)
    else:
        latest_export = builds_instance.get_latest_daily_export()
    logger.info(f'using {latest_export["version"]} for instances tests')
    instances, _ = builds_instance.create_instances(
        f'test_latest_export_{instance_name} ' + (os.environ.get('TEST_GROUP_NAME') or ''),
        't2.2xlarge',
        1,
        instance_cloud=Builds.CloudType.AWS,
        instance_image=latest_export['ami_id'],
        predefined_ssh_username=DEFAULT_IMAGE_USERNAME,
        predefined_ssh_password=DEFAULT_IMAGE_PASSWORD,
        key_name=AUTO_TEST_VM_KEY_PAIR,
        network_security_options=Builds.NetworkSecurityOptions.NoInternet
    )

    for current_instance in instances:
        current_instance.wait_for_ssh()
        try:
            wait_for_booted_for_production(current_instance)
            logger.info('Server is booted for production.')
        except Exception:
            bring_restart_on_reboot_node_log(current_instance, logger)
            # If we fail in setup_method, teardown will not be called. lets terminate the instance.
            current_instance.terminate()
            raise

    return instances


class TestInstancesBase(TestBase):
    def setup_method(self, method):
        super().setup_method(method)
        export_name = pytest.config.option.export_name
        self._instances = setup_instances(self.logger, self.__class__.__name__, export_name=export_name)

    def teardown_method(self, method):
        for current_instance in self._instances:
            try:
                current_instance.terminate()
            except Exception as e:
                print(f'Could not terminate {current_instance}: {e}, bypassing', file=sys.stderr, flush=True)

        super().teardown_method(method)

    @staticmethod
    def connect_node_maker(instance, password=NODE_MAKER_PASSWORD):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(instance.ip, username=NODE_MAKER_USERNAME, password=password, timeout=60,
                       auth_timeout=60, look_for_keys=False, allow_agent=False)
        return client
