import sys
import time

import paramiko
from retrying import retry

from builds import Builds
from builds.builds_factory import BuildsInstance
from ui_tests.tests.ui_test_base import TestBase

from devops.scripts.instances.restart_system_on_reboot import \
    BOOTED_FOR_PRODUCTION_MARKER_PATH

NODE_MAKER_USERNAME = 'node_maker'
NODE_MAKER_PASSWORD = 'M@ke1tRain'

DEFAULT_IMAGE_USERNAME = 'ubuntu'
DEFAULT_IMAGE_PASSWORD = 'bringorder'

DEFAULT_LIMIT = 10

EXPORTS_ENDPOINT = 'exports'
DAILY_EXPORT_SUFFIX = '_daily_export'
DAILY_EXPORT_DATE_FORMAT = '%Y%m%d'


@retry(stop_max_attempt_number=30, wait_fixed=60)
def wait_for_booted_for_production(instance: BuildsInstance):
    print('Waiting for server to be booted for production...')
    test_ready_command = f'ls -al {BOOTED_FOR_PRODUCTION_MARKER_PATH.absolute().as_posix()}'
    state = instance.ssh(test_ready_command)
    assert 'root root' in state[1]


def setup_instances(logger):
    builds_instance = Builds()
    latest_export = builds_instance.get_latest_daily_export()
    logger.info(f'using {latest_export["version"]} for instances tests')
    instances = builds_instance.create_instances(
        'test_latest_export',
        't2.2xlarge',
        1,
        instance_cloud=Builds.CloudType.AWS,
        instance_image=latest_export['ami_id'],
        predefined_ssh_username=DEFAULT_IMAGE_USERNAME,
        predefined_ssh_password=DEFAULT_IMAGE_PASSWORD
    )

    for current_instance in instances:
        current_instance.wait_for_ssh()
        wait_for_booted_for_production(current_instance)

    return instances


class TestInstances(TestBase):
    def setup_method(self, method):
        super().setup_method(method)
        self.__instances = setup_instances(self.logger)

    def teardown_method(self, method):
        for current_instance in self.__instances:
            try:
                current_instance.terminate()
            except Exception:
                print(f'Could not terminate {current_instance}, bypassing', file=sys.stderr, flush=True)

        super().teardown_method(method)

    def test_instances(self):
        # Test that user exists and we can connect to it
        for instance in self.__instances:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                instance.ip, username=NODE_MAKER_USERNAME, password=NODE_MAKER_PASSWORD, timeout=60,
                auth_timeout=60
            )

        # Test that node maker does not exist after login
        for instance in self.__instances:
            assert NODE_MAKER_USERNAME in instance.ssh('cat /etc/passwd')[1]
            self.change_base_url(f'https://{instance.ip}')
            self.signup_page.wait_for_signup_page_to_load()
            self.signup_page.fill_signup_with_defaults_and_save()
            self.login_page.wait_for_login_page_to_load()
            self.login()
            time.sleep(61)
            assert NODE_MAKER_USERNAME not in instance.ssh('cat /etc/passwd')[1]
