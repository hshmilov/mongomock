import os
import sys

import paramiko
from retrying import retry

from builds import Builds
from builds.builds_factory import BuildsInstance
from devops.scripts.instances.restart_system_on_reboot import \
    BOOTED_FOR_PRODUCTION_MARKER_PATH
from ui_tests.tests.ui_test_base import TestBase

NODE_MAKER_USERNAME = 'node_maker'
NODE_MAKER_PASSWORD = 'M@ke1tRain'

DEFAULT_IMAGE_USERNAME = 'ubuntu'
DEFAULT_IMAGE_PASSWORD = 'bringorder'
AUTO_TEST_VM_KEY_PAIR = 'Auto-Test-VM-Key'

DEFAULT_LIMIT = 10


@retry(stop_max_attempt_number=90, wait_fixed=1000 * 20)
def wait_for_booted_for_production(instance: BuildsInstance):
    print('Waiting for server to be booted for production...')
    test_ready_command = f'ls -al {BOOTED_FOR_PRODUCTION_MARKER_PATH.absolute().as_posix()}'
    state = instance.ssh(test_ready_command)
    assert 'root root' in state[1]


def setup_instances(logger):
    builds_instance = Builds()
    latest_export = builds_instance.get_latest_daily_export()
    logger.info(f'using {latest_export["version"]} for instances tests')
    instances, _ = builds_instance.create_instances(
        'test_latest_export ' + (os.environ.get('TEST_GROUP_NAME') or ''),
        't2.2xlarge',
        1,
        instance_cloud=Builds.CloudType.AWS,
        instance_image=latest_export['ami_id'],
        predefined_ssh_username=DEFAULT_IMAGE_USERNAME,
        predefined_ssh_password=DEFAULT_IMAGE_PASSWORD,
        key_name=AUTO_TEST_VM_KEY_PAIR
    )

    for current_instance in instances:
        current_instance.wait_for_ssh()
        try:
            wait_for_booted_for_production(current_instance)
        except Exception:
            # If we fail in setup_method, teardown will not be called. lets terminate the instance.
            current_instance.terminate()
            raise

    return instances


class TestInstancesBase(TestBase):
    def setup_method(self, method):
        super().setup_method(method)
        self._instances = setup_instances(self.logger)

    def teardown_method(self, method):
        for current_instance in self._instances:
            try:
                current_instance.terminate()
            except Exception as e:
                print(f'Could not terminate {current_instance}: {e}, bypassing', file=sys.stderr, flush=True)

        super().teardown_method(method)

    @staticmethod
    def connect_node_maker(instance):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(instance.ip, username=NODE_MAKER_USERNAME, password=NODE_MAKER_PASSWORD, timeout=60,
                       auth_timeout=60, look_for_keys=False, allow_agent=False)
        return client
